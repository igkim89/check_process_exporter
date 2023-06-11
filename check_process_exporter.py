
import time
import argparse
import logging
import psutil
import yaml
from prometheus_client import start_http_server, Gauge

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Setting the arguments
parser = argparse.ArgumentParser()

# required arg
parser.add_argument('-c', '--config', required=False, default="./conf/config.yml", help="configuration file")
parser.add_argument('-p', '--port', required=False, default="9439", help="export http port")
args = parser.parse_args()


class CheckProcessExporter:
    def __init__(self, config:str, port:str) -> None:
        self.config = config
        self.port = port
        self.metric_dict = {}
        with open(self.config) as c:
            self.conf = yaml.safe_load(c)

    def check_process(self, metric_name):
        if self.conf['search_list'][metric_name]['type'] == "process-name":
            psname = self.conf['search_list'][metric_name]['psname']
            for p in psutil.process_iter():
                try:
                    if psname.lower() in p.name().lower():
                        return 1
                    else:
                        continue
                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
                    continue
            return 0
        elif self.conf['search_list'][metric_name]['type'] == "cmdline":
            cmdlist = self.conf['search_list'][metric_name]['cmdlist']
            cmdlist_len = len(cmdlist)
            for p in psutil.process_iter():
                try:
                    match_cnt = 0
                    plist = p.cmdline()
                    if cmdlist_len <= len(plist):
                        for i in range(0, cmdlist_len):
                            if cmdlist[i] == '':
                                match_cnt = match_cnt + 1
                            elif cmdlist[i].lower() in plist[i].lower():
                                match_cnt = match_cnt + 1
                    if match_cnt == cmdlist_len:
                        return 1
                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
                    continue
            return 0

    def create_gauge_for_metric(self, metric_name):
        if self.metric_dict.get(metric_name) is None:
            self.metric_dict[metric_name] = Gauge(metric_name, f"running state of {metric_name}")

    def set_value(self, metric_name):
        self.metric_dict[metric_name].set(self.check_process(metric_name))

    def main(self):
        exporter_port = int(self.port)
        start_http_server(exporter_port)
        logging.info('Starting check_process_exporter.')
        logging.info(f'listening on {exporter_port} port..')

        while True:
            for s in self.conf['search_list']:
                self.create_gauge_for_metric(s)
                self.set_value(s)
            time.sleep(10)


if __name__ == "__main__":
    config, port = args.config, args.port
    c = CheckProcessExporter(config, port)
    c.main()