import random


a = random.randint(1, 100)
print(a)

if a > 50:
    print("a is greater than 50")
else:
    print("a is less than 50")


def hello(a):
    print(f"Hello{a}")


hello(a=a)
