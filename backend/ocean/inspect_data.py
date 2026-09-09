from data import inspect_all

if __name__ == "__main__":
    for dataset in inspect_all():
        print("=" * 80)
        print(dataset["file"])
        print("-" * 80)

        print("Dimensions:")
        for name, size in dataset["dimensions"].items():
            print(f"  {name}: {size}")

        print("\nCoordinates:")
        for name in dataset["coordinates"]:
            print(f"  {name}")

        print("\nVariables:")
        for name in dataset["variables"]:
            print(f"  {name}")

        print("\nAttributes:")
        for name, value in dataset["attributes"].items():
            print(f"  {name}: {value}")