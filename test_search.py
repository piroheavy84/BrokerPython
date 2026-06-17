import json

with open(
    "output/chebanca_index.json",
    encoding="utf-8"
) as f:

    rules = json.load(f)

print()

print("===============================")
print("PRIME 5 REGOLE")
print("===============================")
print()

for rule in rules[:5]:

    print(rule)

    print()