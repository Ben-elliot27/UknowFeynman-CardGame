import time
from collections import Counter

def any_combination_of(values, combinations):
    # Convert the input list to a set
    input_set = set(values)

    # Iterate over each sublist in the comparison list
    for sublist in combinations:
        # Convert the sublist to a set
        sublist_set = set(sublist)
        # Check if input set matches the sublist set
        if input_set == sublist_set:
            return True
    # If no match is found
    return False

def any_combination_of2(values, combinations):
    # Convert the input list to a Counter
    input_counter = Counter(values)

    # Iterate over each sublist in the comparison list
    for sublist in combinations:
        # Convert the sublist to a Counter
        sublist_counter = Counter(sublist)
        # Check if input Counter matches the sublist Counter
        if input_counter == sublist_counter:
            return True
    # If no match is found
    return False

allowed_hadrons = [['u', 'u', 'd'], ['u', 'd', 'd'], ['u', 'd', 'd'], ['u', 'd', 'd'], ['u', 'd', 'd'], ['u', 'd', 'd'], ['u', 'd', 'd'], ['u', 'd', 'd'], ['u', 'd', 'd'], ['u', 'd', 'd'], ['u', 'd', 'd']]

input_l = ['u', 'd', 's', 'm']
t0 = time.time()
print(any_combination_of(input_l, allowed_hadrons))
t1 = time.time()
print(any_combination_of2(input_l, allowed_hadrons))
t2 = time.time()
print("1", t1 - t0)
print("2", t2 - t1)