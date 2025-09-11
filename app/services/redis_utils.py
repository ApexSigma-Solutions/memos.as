def scan_iter(client, match, count=1000):
    """Safely iterate over keys in a Redis database."""
    cursor = "0"
    while True:
        cursor, keys = client.scan(cursor=cursor, match=match, count=count)
        for k in keys:
            yield k
        if cursor == 0 or cursor == "0":
            break
