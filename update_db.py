import labguruApi
import pandas as pd
from os.path import join
import json
import smtplib
from email.message import EmailMessage
import traceback
import logging

CONFIG_FILE = r"config.json"
LOG_FILE = r"log.txt"

def send_error_email(e):
    #stack trace email
    error_email = EmailMessage()
    error_email["Subject"] = "LabGuru report exception"
    error_email["From"] = config.sender_email
    error_email["To"] = config.receiver_email
    error_email["Cc"] = config.email_ccs
    email_body = (
        "LabGuru report exception with the following stack trace\n\n\n{}".format(
            traceback.format_exc()
        )
    )
    error_email.set_content(email_body)
    reciepients = config.email_ccs + [config.receiver_email]
    smtp = smtplib.SMTP_SSL(config.smtp_server, config.smtp_port)
    smtp.login(config.sender_email, config.password_email)
    smtp.send_message(error_email, to_addrs=reciepients)
    smtp.quit()
    logger.info("Stacktrace sent by email")

def send_log_email(e):
    #stack trace email
    log_email = EmailMessage()
    log_email["Subject"] = "LabGuru report log"
    log_email["From"] = config.sender_email
    log_email["To"] = config.receiver_email
    log_email["Cc"] = config.email_ccs
    email_body =  "LabGuru report exception, logs attached"
    log_email.set_content(email_body)
    with open(LOG_FILE, "r") as f:
        logs = f.read()
    log_email.add_attachment(logs)
    reciepients = config.email_ccs + [config.receiver_email]
    smtp = smtplib.SMTP_SSL(config.smtp_server, config.smtp_port)
    smtp.login(config.sender_email, config.password_email)
    smtp.send_message(log_email, to_addrs=reciepients)
    smtp.quit()
    logger.info("Logs sent by email")

time_format = r"%Y-%m-%d %H:%M:%S"
format=r"%(asctime)s - %(levelname)s - %(message)s"

logging.basicConfig(filename=LOG_FILE, format=format, datefmt=time_format)
logger = logging.getLogger("LabGuruReport")
logger.info("LabGuruReport started")

config = labguruApi.LabGuruReportConfig(CONFIG_FILE)
logger.setLevel(config.log_level)
logger.info("Config loaded: {}".format(config.json_config))
# if test use a fake api that loads info from files
logger.info(
    "Launched in testing mode, using FakeGuru APIs"
    if config.is_testing
    else "Launched in production mode, using LabGuru APIs"
)

try:
    labguruApi = (
        labguruApi.FakeGuru(config.token)
        if config.is_testing
        else labguruApi.LabguruApi(config.token)
    )
    # this should raise an error in case of api changes
    if config.is_check_api:
        logger.info("Testing APIs")
        labguruApi.test_apis()
        logger.info("APIs successfully tested")

    # get database, stock and experiment from apis
    database = labguruApi.get_database()
    logger.info("Database retrieved")

    database_ids = [row["id"] for row in database]
    database_by_id = {row["id"]: row for row in database}
    # for each database entry retreive stocks and experiments
    experiments_by_database_id = labguruApi.get_experiments_by_database_id(database_ids)
    logger.info("Experiments retrieved")

    stocks_by_database_id = labguruApi.get_stocks_by_database_id(database_ids)
    logger.info("Stocks retrieved")

    # remove empty database entries
    experiments_by_database_id = {
        id: experiments
        for id, experiments in experiments_by_database_id.items()
        if len(experiments) > 0
    }
    stocks_by_database_id = {
        id: stocks for id, stocks in stocks_by_database_id.items() if len(stocks) > 0
    }

    # flatten dictionary, keep only wanted columns and add a prefix to the name
    def prep_dict(dic, columns, prefix=""):
        flat_dic = pd.json_normalize(dic)
        flat_dic = flat_dic.filter(columns, axis=1)
        if prefix != "":
            mapper = {key: prefix + key for key in columns}
            flat_dic = flat_dic.rename(mapper, axis=1)
        return flat_dic

    # merge, remove unwanted columns and add a prefix
    def merge_to_dataframe(
        items_by_database_id, database_by_id, database_columns, item_columns, prefix
    ):
        prepped_items = []
        prepped_databases = []
        for database_id in items_by_database_id.keys():
            for item in items_by_database_id[database_id]:
                prepped_items.append(prep_dict(item, item_columns, prefix))
                prepped_databases.append(
                    prep_dict(database_by_id[database_id], database_columns)
                )

        prepped_items = (
            pd.concat(prepped_items, axis=0)
            .sort_values(prefix + "id")
            .reset_index(drop=True)
        )
        prepped_databases = (
            pd.concat(prepped_databases, axis=0)
            .sort_values("id")
            .reset_index(drop=True)
        )
        data = pd.concat([prepped_databases, prepped_items], axis=1)
        return data

    experiment_data = merge_to_dataframe(
        experiments_by_database_id,
        database_by_id,
        config.database_columns,
        config.experiment_columns,
        "experiment_",
    )
    stock_data = merge_to_dataframe(
        stocks_by_database_id,
        database_by_id,
        config.database_columns,
        config.stock_columns,
        "stock_",
    )
    experiment_data_path = join(config.save_path, "experiment_data.csv")
    experiment_data.to_csv(experiment_data_path, index=False)
    logger.info("Experiments data written to: {}".format(experiment_data_path))

    stock_data_path = join(config.save_path, "stock_data.csv")
    stock_data.to_csv(stock_data_path, index=False)
    logger.info("Stocks data written to: {}".format(stock_data_path))
    logger.info("LabGuruReport ended")


except Exception as e:
    logger.exception("Unhandled exception")
    if config.email_on_exception:
        send_error_email(e)
    if config.email_logs_on_exception:
        send_log_email(e)

