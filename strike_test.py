from strikes import add_strike, get_strikes

CHAT = 123
USER = 999

for i in range(5):

    strikes, action = add_strike(
        CHAT,
        USER,
        "TestUser",
        "Spam"
    )

    print(
        f"Strike {strikes} -> {action}"
    )

print("Final:", get_strikes(CHAT, USER))
