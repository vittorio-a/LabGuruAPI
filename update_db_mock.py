import labguruApi
import json

CONFIG_FILE = r"config.json"
MOCK_ID = 1049
MOCK_EXP = "exp.txt"
MOCK_STK = "stk.txt"

config = labguruApi.LabGuruReportConfig(CONFIG_FILE)

labguruApi = labguruApi.LabguruApi(config.token)

mock_experiment = labguruApi.get_experiments_by_database_id([MOCK_ID])[MOCK_ID]
with open(MOCK_EXP, "w") as f:
    json.dump(mock_experiment, f)

mock_stock = labguruApi.get_stocks_by_database_id([MOCK_ID])[MOCK_ID]
with open(MOCK_STK, "w") as f:
    json.dump(mock_stock, f)

