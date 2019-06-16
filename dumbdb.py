class DumbDB(object):
    def __init__(self, db_path):
        self.db_path = db_path

    def add(self, resource_id):
        with open(self.db_path, "a") as f:
            f.write(str(resource_id))
            f.write('\n')

    def exists(self, resource_id):
        str_id = str(resource_id)
        try:
            with open(self.db_path, 'r') as f:
                for line in f:
                    if line.strip() == str_id:
                        return True
        except FileNotFoundError:
            pass

        return False
