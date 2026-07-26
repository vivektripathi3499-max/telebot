from spam import check_spam

CHAT_ID = 123
USER_ID = 456

tests = [
    ("Normal message", "Hello everyone!"),
    ("10 emojis", "😂" * 10),
    ("20 emojis", "😂" * 20),
    ("50 emojis", "😂" * 50),
    ("Flood test", "spam"),
]

print("=" * 60)

for title, msg in tests:
    result = check_spam(CHAT_ID, USER_ID, msg)
    print(f"\n{title}")
    print(result)

print("\nFlooding Test")

for i in range(6):
    result = check_spam(CHAT_ID, USER_ID + 1, "hello")
    print(f"{i+1}: {result}")
