import os

from file_constants import TEST_DATA_DIR


def dynamic(namespace):
    """
    Decorator.
    @dynamic(globals()) before a subclass of unittest.TestCase
    creates versions of that test for each dataset
    """
    def dynamic_inner(test_class):
        datasets = []
        for file in os.scandir(TEST_DATA_DIR):
            if file.name[-5:] == ".json":
                datasets.append(file.name[:-5])

        for dataset in datasets:
            class_name = dataset + "_" + test_class.__name__
            namespace[class_name] = type(class_name, (test_class,), {"dataset": dataset})

    return dynamic_inner
