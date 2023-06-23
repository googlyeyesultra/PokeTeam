import analyze
from file_constants import *


def get_test_md(dataset):
    metagame = TEST_DATA_DIR + dataset + ".json"
    threats = TEST_DATA_DIR + dataset + THREAT_FILE
    team = TEST_DATA_DIR + dataset + TEAMMATE_FILE
    return analyze.MetagameData(metagame, threats, team)


def get_custom_test_md(dataset):
    metagame = CUSTOM_TEST_DATA_DIR + dataset + ".json"
    threats = CUSTOM_TEST_DATA_DIR + dataset + THREAT_FILE
    team = CUSTOM_TEST_DATA_DIR + dataset + TEAMMATE_FILE
    return analyze.MetagameData(metagame, threats, team)
