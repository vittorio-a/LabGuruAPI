import requests
import json
import typing

class LabGuruReportConfig:
    """Loads the configuration file for LabGuruReport
    """
    def __init__(self, config_file) -> None:
        with open(config_file, "r") as f:
            config = json.load(f)
        self.json_config = config
        self.database_columns = config["database_columns"]
        self.experiment_columns = config["experiment_columns"]
        self.stock_columns = config["stock_columns"]
        # commented for gmail API change
        # self.sender_email = config["email"]
        # self.receiver_email = config["email_receiver"]
        # self.password_email = config["email_password"]
        # self.email_ccs = config["email_ccs"]
        # self.smtp_server = config["smtp_server"]
        # self.smtp_port = config["smtp_port"]
        # self.email_on_exception = config["email_on_exception"]
        self.save_path = config["save_path"]
        self.token = config["token"]
        self.is_testing = config["is_testing"]
        self.is_check_api = config["is_check_api"]
        self.log_level = config["log_level"]
        #self.email_logs_on_exception = ["email_logs_on_exception"]


class LabguruApi:
    # Endpoints definitions
    API_BASE_URL = r"https://eu.labguru.com/api/v1/"
    ENDPOINT_EXPERIMENT = API_BASE_URL + r"experiments"
    ENDPOINT_ELEMENT = API_BASE_URL + r"elements/"
    ENDPOINT_UUID =  r"blob:https://eu.labguru.com/"
    ENDPOINT_ITEM_EXPERIMENT = API_BASE_URL + r"experiments/item_experiments"
    ENDPOINT_ITEM_STOCK = API_BASE_URL + r"stocks/item_stocks"
    ENDPOINT_DATABASE = API_BASE_URL + r"biocollections/database"

    # Mock used to test the APIs
    MOCK_DATABASE_ID = 1049
    MOCK_EXPECTED_EXPERIMENTS = r"exp.txt"
    MOCK_EXPECTED_STOCKS = r"stk.txt"

    # Error texts
    ERROR_MOCK_STOCK_LEN = (
        "The number of the received stocks does not match the expected one"
    )
    ERROR_MOCK_EXPERIMENTS_LEN = (
        "The number of the received experiments does not match the expected one"
    )
    ERROR_MOCK_STOCK = "The stocks received do not match up with the expected ones"
    ERROR_MOCK_EXPERIMENTS = (
        "The experiments received do not match up with the expected ones"
    )

    def __init__(self, token) -> None:
        self.session = requests.session()
        self.session.params = {"token": token}

    def _handle_exepction(self, e) -> None:
        raise e

    def _get_with_pagination(self, url: str, params: dict) -> dict:
        # shared method to do pagination
        # parameters needed to paginate
        pagination_params = {"meta": "true", "page": 1, "pageSize": 200}
        params = {**params, **pagination_params}
        response = self.session.get(url, params=params).json()
        # meta contains the pagination informations
        response_meta = response["meta"]
        response_data = response["data"]
        response_data_full = response_data
        # do the call until you have finished the items, the pages
        # or the last call data was empty
        while (
            (int(params["page"]) < int(response_meta["page_count"]))
            and (len(response_data) > 0)
            and (len(response_data_full) < response_meta["item_count"])
        ):
            params["page"] = params["page"] + 1
            response = self.session.get(url, params=params).json()
            response_meta = response["meta"]
            response_data = response["data"]
            response_data_full.extend(response_data)
        return response_data_full

    def get_database(self) -> typing.List[dict]:
        """Get the full inventory database collection

        Returns:
            typing.List[dict]: list of database entries
        """
        try:
            databse = self._get_with_pagination(self.ENDPOINT_DATABASE, params={})
        except Exception as e:
            self._handle_exepction(e)
        return databse

    def get_database_stock(self, database_id: int) -> typing.List[dict]:
        """Get the stocks associated with a database entry

        Args:
            database_id (int): the id of the database entry

        Returns:
            typing.List[dict]: list of stocks
        """
        params = {
            "kendo": "true",
            # "exclude_fields": "signed_by,witnessed_by,editors,sections,attachments,gantt,"
            # "external_uuid,links,tags,uuid,current_step,identifier,duplicate_of,deleted_at,"
            # "deleted_by,witnessed_by,project_owner,user",
            "item_type": "Biocollections::Generic",
            "item_id": database_id,
            "from": "/biocollections/database/" + str(database_id),
            "filter[filters][0][field]": "storage_id",
        }
        try:
            stocks = self._get_with_pagination(self.ENDPOINT_ITEM_STOCK, params=params)
        except Exception as e:
            self._handle_exepction(e)
        return stocks

    def get_database_experiments(self, database_id: int) -> typing.List[dict]:
        """Get the experiments associated with a database entry

        Args:
            database_id (int): the id of the database entry

        Returns:
            typing.List[dict]: list of experiments
        """
        params = {
            "kendo": "true",
            # "exclude_fields": "signed_by,results,witnessed_by,editors,sections,attachments"
            # ",gantt,external_uuid,links,tags,current_step,identifier,duplicate_of,deleted_at"
            # ",deleted_by,witnessed_by,project_owner,user,custom_fields_as_hash,"
            # "class_display_name,linked_resources,updated_by",
            "pathname": "/biocollections/database/" + str(database_id),
            "item_id": database_id,
            "item_class": "Biocollections::Generic",
            # "sort[0][field]": "updated_at",
            # "sort[0][dir]": "desc",
        }
        try:
            experiments = self._get_with_pagination(
                self.ENDPOINT_ITEM_EXPERIMENT, params=params
            )
        except Exception as e:
            self._handle_exepction(e)
        return experiments

    def get_experiments_by_database_id(
        self, database_ids: typing.List[int]
    ) -> dict:
        """Get all the experiments associated with a list of databases entries

        Args:
            database_ids (typing.List[int]): list of database ids for which to
            retrieve the associated experiments

        Returns:
            dict: dictionary of experiments where the keys are the database id
        """
        return {
            database_id: self.get_database_experiments(database_id)
            for database_id in database_ids
        }

    def get_stocks_by_database_id(
        self, database_ids: typing.List[int]
    ) -> dict:
        """Get all the stocks associated with a list of databases entries

        Args:
            database_ids (typing.List[int]): list of database ids for which to
            retrieve the associated stocks

        Returns:
            dict: dictionary of stocks where the keys are the database id
        """
        return {
            database_id: self.get_database_stock(database_id)
            for database_id in database_ids
        }

    def _test_failure(self, exception) -> None:
        raise exception

    def test_apis(self) -> None:
        """Test the APIs by doing a mock call

        It will retrieve the stocks and experiment associated with
        mock items and check that they are equals to the expected values
        """
        try:
            with open(self.MOCK_EXPECTED_EXPERIMENTS, "r") as f:
                mock_expected_experiments = json.load(f)
            with open(self.MOCK_EXPECTED_STOCKS, "r") as f:
                mock_expected_stocks = json.load(f)
            mock_api_experiments = self.get_database_experiments(self.MOCK_DATABASE_ID)
            mock_api_stocks = self.get_database_stock(self.MOCK_DATABASE_ID)

            assert len(mock_api_experiments) == len(
                mock_expected_experiments
            ), self.ERROR_MOCK_EXPERIMENTS_LEN
            assert len(mock_api_stocks) == len(
                mock_expected_stocks
            ), self.ERROR_MOCK_STOCK_LEN
            for expected_experiment in mock_expected_experiments:
                expected_id = expected_experiment["id"]
                api_expected = None
                for api_experiment in mock_api_experiments:
                    if api_experiment["id"] == expected_id:
                        api_expected = api_experiment
                        break
                assert api_expected == expected_experiment, self.ERROR_MOCK_EXPERIMENTS

            for expected_stock in mock_expected_stocks:
                expected_id = expected_stock["id"]
                api_expected = None
                for api_stock in mock_api_stocks:
                    if api_stock["id"] == expected_id:
                        api_expected = api_stock
                        break
                assert api_expected == expected_stock, self.ERROR_MOCK_STOCK
        except Exception as e:
            self._test_failure(e)

    def get_experiment_by_id(self, id: int):
        return self.session.get(self.ENDPOINT_EXPERIMENT + "/" + str(id)).json()

    def get_excel_elements_list_by_experiment_id(self, id: int):
        experiment = self.get_experiment_by_id(id)
        exel_ids = []
        for procedure in experiment["experiment_procedures"]:
            for element in procedure['experiment_procedure']["elements"]:
                if element["element_type"] == "excel":
                    exel_ids.append(element["id"])
        return exel_ids

    def get_element_by_id(self, id: int):
        return self.session.get(self.ENDPOINT_ELEMENT + str(id)).json()


class FakeGuru:
    FAKE_DATABASE = "database.json"
    FAKE_EXPERIMENTS = "experiments.json"
    FAKE_STOCKS = "stocks.json"

    def __init__(self, token) -> None:
        pass

    def get_database(self) -> typing.List[dict]:
        """Get the full inventory database collection

        Returns:
            typing.List[dict]: list of database entries
        """
        with open(self.FAKE_DATABASE, "r") as f:
            database = json.load(f)
        return database

    def get_experiments_by_database_id(
        self, database_ids: typing.List[int]
    ) -> typing.List[dict]:
        """Get all the experiments associated with a list of databases entries

        Args:
            database_ids (typing.List[int]): list of database ids for which to
            retrieve the associated experiments

        Returns:
            typing.List[dict]: list of experiments
        """
        with open(self.FAKE_EXPERIMENTS, "r") as f:
            experiments = json.load(f)
        experiments = {int(key):value for key, value in experiments.items()}
        return experiments

    def get_stocks_by_database_id(
        self, database_ids: typing.List[int]
    ) -> typing.List[dict]:
        """Get all the stocks associated with a list of databases entries

        Args:
            database_ids (typing.List[int]): list of database ids for which to
            retrieve the associated stocks

        Returns:
            typing.List[dict]: list of stocks
        """
        with open(self.FAKE_STOCKS, "r") as f:
            stocks = json.load(f)
        stocks = {int(key):value for key, value in stocks.items()}
        return stocks

    def test_apis(self) -> None:
        """Test the APIs by doing a mock call

        It will retrieve the stocks and experiment associated with
        mock items and check that they are equals to the expected values
        """
        pass
