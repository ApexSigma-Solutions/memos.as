#!/usr/bin/env python3
"""
Chat Thread Summarizer with Progress Logging for MemOS.as

This script takes chat threads, summarizes them, and automatically saves progress
with environment snapshots to memOS.as for historical tracking.
Specialized for MemOS memory management and agent memory protocol.
"""

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

# Skip service imports for now to avoid database connection issues
MEMOS_SERVICES_AVAILABLE = False


class MemOSThreadSummarizer:
    """Summarizes chat threads with MemOS memory protocol focus."""

    def __init__(self, memos_base_url: str = "http://devenviro_memos_api:8090"):
        """Initialize the MemOS summarizer."""
        self.memos_base_url = memos_base_url
        self.session_id = f"memos_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    async def summarize_chat_thread(
        self, chat_file_path: str, output_dir: str = None, save_progress: bool = True
    ) -> Dict[str, Any]:
        """
        Summarize a chat thread with MemOS context.

        Args:
            chat_file_path: Path to chat thread file
            output_dir: Directory to save summary (optional)
            save_progress: Whether to save progress to memOS.as

        Returns:
            Dictionary containing summary results
        """

        print("MEMOS CHAT THREAD SUMMARIZER")
        print("=" * 50)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Session ID: {self.session_id}")
        print()

        # Load chat thread
        chat_data = await self._load_chat_thread(chat_file_path)

        # Create MemOS-specific environment snapshot
        env_snapshot = await self._create_memos_snapshot()

        # Generate summary with memory focus
        summary = await self._generate_memory_summary(chat_data, env_snapshot)

        # Save summary to file if requested
        if output_dir:
            await self._save_summary_to_file(summary, output_dir)

        # Save progress using memory protocol
        if save_progress:
            await self._save_progress_to_memos(summary, env_snapshot)

        print("SUCCESS: MemOS chat thread summarization completed!")
        return summary

    async def _load_chat_thread(self, file_path: str) -> Dict[str, Any]:
        """Load and parse chat thread from file."""

        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Chat thread file not found: {file_path}")

        print(f"Loading chat thread: {file_path}")

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")

            # Try to parse as JSON first
            try:
                chat_data = json.loads(content)
                print("   Format: JSON")
            except json.JSONDecodeError:
                # Treat as plain text and structure it
                chat_data = {
                    "format": "text",
                    "content": content,
                    "lines": content.splitlines(),
                    "word_count": len(content.split()),
                    "char_count": len(content),
                }
                print("   Format: Plain text")

            print(f"   Size: {file_path.stat().st_size} bytes")

            # Add metadata
            chat_data["metadata"] = {
                "file_path": str(file_path),
                "file_size": file_path.stat().st_size,
                "loaded_at": datetime.now().isoformat(),
                "content_hash": hashlib.sha256(content.encode()).hexdigest()[:16],
            }

            return chat_data

        except Exception as e:
            print(f"❌ Error loading chat thread: {e}")
            raise

    async def _create_memos_snapshot(self) -> Dict[str, Any]:
        """Create a MemOS-specific snapshot of the memory environment."""

        print("Creating MemOS environment snapshot...")

        try:
            import subprocess

            # Get git status
            try:
                git_status = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    cwd=Path(__file__).parent.parent,
                )
                git_changes = (
                    git_status.stdout.strip().splitlines()
                    if git_status.returncode == 0
                    else []
                )
            except Exception:
                git_changes = ["git_not_available"]

            # Get recent git commits
            try:
                git_log = subprocess.run(
                    ["git", "log", "--oneline", "-5"],
                    capture_output=True,
                    text=True,
                    cwd=Path(__file__).parent.parent,
                )
                recent_commits = (
                    git_log.stdout.strip().splitlines()
                    if git_log.returncode == 0
                    else []
                )
            except Exception as e:
                recent_commits = [f"git_log_not_available: {e}"]

            # Get MemOS containers specifically
            try:
                docker_ps = subprocess.run(
                    [
                        "docker",
                        "ps",
                        "--filter",
                        "name=memos",
                        "--format",
                        "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}",
                    ],
                    capture_output=True,
                    text=True,
                )
                memos_containers = (
                    docker_ps.stdout.strip().splitlines()
                    if docker_ps.returncode == 0
                    else []
                )
            except Exception:
                memos_containers = ["docker_not_available"]

            # Get network status
            try:
                network_inspect = subprocess.run(
                    [
                        "docker",
                        "network",
                        "inspect",
                        "apexsigma_net",
                        "--format",
                        "{{range .Containers}}{{.Name}} {{end}}",
                    ],
                    capture_output=True,
                    text=True,
                )
                network_containers = (
                    network_inspect.stdout.strip().split()
                    if network_inspect.returncode == 0
                    else []
                )
            except Exception:
                network_containers = ["network_not_available"]

            # Check memory storage status
            memory_status = {
                "postgres_active": "postgres" in " ".join(memos_containers).lower(),
                "redis_active": "redis" in " ".join(network_containers).lower(),
                "qdrant_active": "qdrant" in " ".join(network_containers).lower(),
                "neo4j_active": "neo4j" in " ".join(network_containers).lower(),
            }

            snapshot = {
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                "service": "memos.as",
                "environment": {
                    "git_changes": git_changes,
                    "recent_commits": recent_commits,
                    "memos_containers": memos_containers,
                    "network_containers": network_containers,
                    "python_version": sys.version,
                    "working_directory": str(Path.cwd()),
                },
                "memos_status": {
                    "containers_running": len(
                        [c for c in memos_containers if "Up" in c]
                    ),
                    "network_unified": "apexsigma_net" in " ".join(network_containers),
                    "memory_tier_ready": all(memory_status.values()),
                    "storage_systems": memory_status,
                    "memory_protocol": "active",
                },
            }

            print(f"   Git changes: {len(git_changes)}")
            print(f"   MemOS containers: {len(memos_containers) - 1}")  # -1 for header
            print(f"   Memory tiers active: {sum(memory_status.values())}/4")

            return snapshot

        except Exception as e:
            print(f"⚠️  MemOS snapshot limited due to error: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                "service": "memos.as",
                "environment": {"error": str(e)},
                "memos_status": {"error": "could_not_determine"},
            }

    async def _generate_memory_summary(
        self, chat_data: Dict[str, Any], env_snapshot: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate summary with focus on memory operations."""

        print("Generating MemOS memory-focused summary...")

        # Extract key information based on content type
        if chat_data.get("format") == "text":
            content = chat_data["content"]
            lines = chat_data["lines"]
        else:
            # Handle JSON format
            content = json.dumps(chat_data, indent=2)
            lines = content.splitlines()

        # Basic analysis
        analysis = {
            "content_type": chat_data.get("format", "unknown"),
            "total_lines": len(lines),
            "total_words": len(content.split()),
            "total_characters": len(content),
            "estimated_reading_time_minutes": len(content.split())
            / 200,  # 200 wpm average
        }

        # MemOS-specific keywords
        content_lower = content.lower()

        # Memory and storage keywords
        memos_keywords = {
            "memory": content_lower.count("memory"),
            "memos": content_lower.count("memos"),
            "context": content_lower.count("context"),
            "storage": content_lower.count("storage"),
            "postgres": content_lower.count("postgres"),
            "redis": content_lower.count("redis"),
            "qdrant": content_lower.count("qdrant"),
            "neo4j": content_lower.count("neo4j"),
            "vector": content_lower.count("vector"),
            "graph": content_lower.count("graph"),
            "cache": content_lower.count("cache"),
            "retrieve": content_lower.count("retrieve"),
            "store": content_lower.count("store"),
            "query": content_lower.count("query"),
        }

        # Find memory-related sections
        important_lines = []
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(
                keyword in line_lower
                for keyword in [
                    "memory",
                    "memos",
                    "memory",
                    "context",
                    "storage",
                    "retrieve",
                    "store",
                    "error",
                    "success",
                    "complete",
                    "failed",
                ]
            ):
                important_lines.append(
                    {
                        "line_number": i + 1,
                        "content": line.strip()[:100] + "..."
                        if len(line.strip()) > 100
                        else line.strip(),
                    }
                )

        # Generate summary
        summary = {
            "session_id": self.session_id,
            "service": "memos.as",
            "generated_at": datetime.now().isoformat(),
            "source_file": chat_data["metadata"]["file_path"],
            "source_hash": chat_data["metadata"]["content_hash"],
            "analysis": analysis,
            "memos_keywords": memos_keywords,
            "important_sections": important_lines[:12],  # Top 12 for MemOS
            "environment_snapshot": env_snapshot,
            "summary_text": self._generate_memos_summary_text(
                analysis, memos_keywords, important_lines
            ),
            "recommendations": self._generate_memos_recommendations(
                memos_keywords, env_snapshot
            ),
        }

        print(f"   Content analyzed: {analysis['total_words']} words")
        print(f"   Memory-related sections found: {len(important_lines)}")
        print(
            f"   Top MemOS keywords: {sorted(memos_keywords.items(), key=lambda x: x[1], reverse=True)[:3]}"
        )

        return summary

    def _generate_memos_summary_text(
        self, analysis: Dict, keywords: Dict, important_lines: List
    ) -> str:
        """Generate MemOS-focused summary text."""

        top_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:3]
        top_keywords_text = ", ".join([f"{k} ({v})" for k, v in top_keywords if v > 0])

        summary_text = f"""
MemOS Chat Thread Summary:

Content: {analysis["total_words"]} words across {analysis["total_lines"]} lines
Reading Time: ~{analysis["estimated_reading_time_minutes"]:.1f} minutes

Key Memory Topics: {top_keywords_text}

Important Memory Operations:
"""

        for item in important_lines[:5]:
            summary_text += f"- Line {item['line_number']}: {item['content']}\n"

        return summary_text.strip()

    def _generate_memos_recommendations(
        self, keywords: Dict, env_snapshot: Dict
    ) -> List[str]:
        """Generate MemOS-specific recommendations."""

        recommendations = []

        # Memory-focused recommendations
        if keywords.get("memory", 0) > 5:
            recommendations.append(
                "Heavy memory operations detected - review memory protocol usage"
            )

        if keywords.get("context", 0) > 3:
            recommendations.append(
                "Context operations active - consider context database optimization"
            )

        if keywords.get("vector", 0) > 2:
            recommendations.append(
                "Vector operations noted - check Qdrant performance metrics"
            )

        if keywords.get("retrieve", 0) + keywords.get("store", 0) > 5:
            recommendations.append(
                "High storage activity - monitor tiered memory performance"
            )

        # Environment-based recommendations
        if env_snapshot.get("memos_status", {}).get("memory_tier_ready"):
            recommendations.append(
                "All memory tiers operational - optimal for complex memory operations"
            )

        if not env_snapshot.get("memos_status", {}).get("memory_tier_ready"):
            recommendations.append(
                "Memory tiers incomplete - verify Postgres/Redis/Qdrant/Neo4j connectivity"
            )

        if len(env_snapshot.get("environment", {}).get("git_changes", [])) > 6:
            recommendations.append(
                "Significant memory system changes - consider memory protocol validation"
            )

        return recommendations

    async def _save_summary_to_file(
        self, summary: Dict[str, Any], output_dir: str
    ) -> None:
        """Save summary to file."""

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save as JSON
        json_file = output_path / f"memos_chat_summary_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        # Save as markdown
        md_file = output_path / f"memos_chat_summary_{timestamp}.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write("# MemOS Chat Thread Summary\n\n")
            f.write(f"**Generated**: {summary['generated_at']}\\n")
            f.write(f"**Session**: {summary['session_id']}\\n")
            f.write(f"**Service**: {summary['service']}\\n")
            f.write(f"**Source**: {summary['source_file']}\\n\\n")
            f.write(summary["summary_text"])
            f.write("\\n\\n## MemOS Recommendations\\n\\n")
            for rec in summary["recommendations"]:
                f.write(f"- {rec}\\n")

        print("MemOS summary saved to:")
        print(f"   JSON: {json_file}")
        print(f"   Markdown: {md_file}")

    async def _save_progress_to_memos(
        self, summary: Dict[str, Any], env_snapshot: Dict[str, Any]
    ) -> None:
        """Save progress using memory protocol."""

        print("Saving MemOS progress using memory protocol...")

        try:
            # Use direct HTTP client for memory protocol
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Prepare MemOS-specific progress log
                progress_data = {
                    "content": f"MEMOS CHAT SUMMARY: Processed {summary['analysis']['total_words']} words with memory operation focus. Key topics: {', '.join([k for k, v in summary['memos_keywords'].items() if v > 0][:3])}. Memory tier snapshot captured - {sum(env_snapshot['memos_status'].get('storage_systems', {}).values())}/4 systems active.",
                    "metadata": {
                        "source": "MemOSThreadSummarizer",
                        "service": "memos.as",
                        "session_id": summary["session_id"],
                        "event_type": "memos_chat_summary_completed",
                        "timestamp": summary["generated_at"],
                        "priority": "HIGH",
                        "summary_stats": summary["analysis"],
                        "memos_keywords": summary["memos_keywords"],
                        "environment_snapshot": env_snapshot,
                        "source_file": summary["source_file"],
                        "source_hash": summary["source_hash"],
                        "recommendations": summary["recommendations"],
                        "memory_protocol": True,
                        "memory_focus": True,
                    },
                }

                # Send to memOS.as via memory
                response = await client.post(
                    f"{self.memos_base_url}/memory/store",
                    json=progress_data,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    result = response.json()
                    print(
                        f"SUCCESS: MemOS progress saved via memory (Memory ID: {result.get('memory_id')})"
                    )
                else:
                    print(f"WARNING: Failed to save via memory: {response.status_code}")

        except Exception as e:
            print(f"WARNING: Could not save MemOS progress via memory: {e}")


async def main():
    """Main entry point for MemOS chat thread summarizer."""

    parser = argparse.ArgumentParser(
        description="Summarize chat threads with MemOS memory focus and memory protocol logging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
MemOS Examples:
  python chat_thread_summarizer.py memory_chat.txt                   # Summarize memory operations
  python chat_thread_summarizer.py chat.txt --output ./summaries     # Save to custom directory
  python chat_thread_summarizer.py chat.txt --no-progress            # Skip memory logging
        """,
    )

    parser.add_argument("chat_file", help="Path to chat thread file to summarize")

    parser.add_argument(
        "--output",
        metavar="DIR",
        help="Output directory for summary files (default: ./docs/summaries/)",
    )

    parser.add_argument(
        "--no-progress", action="store_true", help="Skip saving progress to memOS.as"
    )

    parser.add_argument(
        "--memos-url",
        default="http://devenviro_memos_api:8090",
        help="memOS.as base URL (default: http://devenviro_memos_api:8090)",
    )

    args = parser.parse_args()

    # Default output directory
    if not args.output:
        args.output = Path("docs/summaries")

    # Create summarizer
    summarizer = MemOSThreadSummarizer(memos_base_url=args.memos_url)

    try:
        # Run summarization
        summary = await summarizer.summarize_chat_thread(
            chat_file_path=args.chat_file,
            output_dir=args.output,
            save_progress=not args.no_progress,
        )

        print()
        print("MEMOS SUMMARY RESULTS")
        print("-" * 25)
        print(f"Words processed: {summary['analysis']['total_words']}")
        print(f"Memory sections: {len(summary['important_sections'])}")
        print(f"Recommendations: {len(summary['recommendations'])}")
        print(f"Session ID: {summary['session_id']}")

        print()
        print("SUCCESS: MemOS chat thread summarization completed successfully!")

    except Exception as e:
        print(f"\\nERROR: MemOS summarization failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("ApexSigma MemOS Chat Thread Summarizer")
    print("memory protocol focus with tiered memory logging")
    print()

    asyncio.run(main())
