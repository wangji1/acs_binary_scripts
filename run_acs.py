"""
Copyright (C) 2018 Intel Corporation

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions
and limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

import os
import time
import shutil
import yaml
import argparse
import subprocess

SHARED_LOG_FOLDER = "/share/opentaas/logs"
DUTINFO_FILE = "/share/opentaas/devices/dutInfo.yaml"
ACS_REPORTS_FOLDER = "_Reports"

ACS_PACKAGE_PATH = "./acs_bin_package"
ACS_BIN = ACS_PACKAGE_PATH + "/acs/acs/ACS"
ACS_BENCH_CONFIG = "OTC/BENCHCFG/benchConfig"
ACS_LOG_LEVEL = "INFO"

PARAM_WIFI = "WIFI"
PARAM_WIFI_AP = "WiFi_Connection_Ap_Name"
PARAM_WIFI_PASSWD = "WiFi_Connection_Passwd"
PARAM_WIFI_SECURITY = "WiFi_Connection_Security_Mode"
PARAM_BT_NAME = "Bt_Device_Name"

TCR_REPORT_LIB = "Core.Report.Live.TcrReportUtils.TcrReport.TcrReport"
TCR_REPORT_API_URL = "\"http://10.239.168.162/acs\""
TCR_REPORT_WEB_URL_PREFIX = "\"http://10.239.168.162/#\""


def run_cmd(cmd, timeout=30):
    """
    run the cmd and return (ret_code, output_buf)
    """
    # run the cmd, and redirct stderr to stdout
    p = subprocess.Popen(args=cmd, shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    elipse = 0
    while elipse < timeout:
        exit_code = p.poll()
        if exit_code is not None:  # cmd done
            break
        elipse += 0.1
        time.sleep(0.1)
    else:  # cmd timeout
        p.kill()
        raise Exception("CMD: '%s' timeout after %ss" % (cmd, timeout))
    buf = p.stdout.read()
    return (exit_code, buf)


class ADB(object):

    def __init__(self, serial=None):
        if serial is None:
            devices = self.get_devices()
            if not devices:
                raise Exception("No device found")
            self.serial = devices[0]
        else:
            self.serial = serial

    @staticmethod
    def get_devices():
        """
        get first all available device
        """
        ret, buf = run_cmd("adb devices")
        lines = buf.split('\n')[1:]  # first line should not included
        devices = []
        for l in lines:
            parts = l.split()
            if len(parts) == 2 and parts[1] == "device":
                devices.append(parts[0])
        return devices

    def get_serial(self):
        """
        return adb serial number
        """
        return self.serial

    def is_online(self):
        """
        check if device is online
        """
        if self.serial in self.get_devices():
            return True
        else:
            return False

    def cmd(self, cmd):
        """
        run adb cmd, return the output buf
        """
        full_cmd = """adb -s %s %s """ % (self.serial, cmd)
        ret, buf = run_cmd(full_cmd)
        return buf

    def shell(self, cmd):
        """
        run 'adb shell' cmd
        """
        full_cmd = """shell '%s' """ % cmd
        return self.cmd(full_cmd)


class runner(object):

    def __init__(self, args):
        self._log_file = ".log"
        self._campaign = args.campaign_name
        self._log_id = args.log_id
        self._enable_tcr = False
        if args.enable_tcr:
            self._enable_tcr = True
        self._adb_connection = None

    def init_logger_file(self):
        """
        Initialize log file name
        """
        if self._log_id is not None:
            self._log_file = '-' + self._log_id + self._log_file
        self._log_file = '-' + 'acs-result' + self._log_file
        if self._campaign is not None:
            self._log_file = '-' + self._campaign + self._log_file
        t = time.strftime('%Y-%m-%d-%H-%M-%S',time.localtime())
        self._log_file = t + self._log_file
        if os.path.exists(SHARED_LOG_FOLDER):
            self._log_file = os.path.join(SHARED_LOG_FOLDER, self._log_file)
        self.logger('Execute command:')
        self.logger('        python run_acs.py')
        self.logger('Parameters:')
        self.logger('        Campaign: {}'.format(self._campaign))
        self.logger('        Log ID: {}'.format(self._log_id))
        self.logger('        Enable TCR: {}'.format(self._enable_tcr))

    def logger(self, content):
        """
        print log and save to file
        """
        if content is not None:
            print str(content)
            if self._log_file is not None:
                f = open(self._log_file, 'a')
                f.write(str(content))
                f.write('\n')
                f.close()

    def share_logs(self):
        """
        copy all the log files to shared folder
        """
        if os.path.exists(SHARED_LOG_FOLDER):
            self.logger('Move all the logs to shared folder: {}'.format(SHARED_LOG_FOLDER))
            if os.path.isdir(ACS_REPORTS_FOLDER):
                reports = os.listdir(ACS_REPORTS_FOLDER)
                for r in reports:
                    report = os.path.join(ACS_REPORTS_FOLDER, r)
                    if os.path.isdir(report):
                        shutil.move(report, SHARED_LOG_FOLDER)

    def run(self):
        """
        integrate all parameters and run ACS campaign
        """        
        params = "-b %s --ll %s" % (ACS_BENCH_CONFIG, ACS_LOG_LEVEL)

        campaign_path = os.path.join(os.getcwd(), ACS_PACKAGE_PATH,
                                     "acs_test_suites/OTC/CAMPAIGN/Celadon/")
        if os.path.exists("%s%s.xml" % (campaign_path, self._campaign)):
            compaign_file = "OTC/CAMPAIGN/Celadon/%s" % self._campaign
        elif os.path.exists("%s%s_APL.xml" % (campaign_path, self._campaign)):
            compaign_file = "OTC/CAMPAIGN/Celadon/%s_APL" % self._campaign
        else:
            raise Exception("Campaign file does not exist, stop testing.")
        params += " -c %s" % compaign_file

        if os.path.exists(DUTINFO_FILE):
            with open(DUTINFO_FILE) as f:
                dut_info = yaml.load(f)
            wifi_info = dut_info.get(PARAM_WIFI)
            if wifi_info is not None:
                print wifi_info
                if wifi_info.get(PARAM_WIFI_AP) is not None:
                    params += " -o %s=%s" % (PARAM_WIFI_AP, wifi_info.get(PARAM_WIFI_AP))
                if wifi_info.get(PARAM_WIFI_PASSWD) is not None:
                    params += " -o %s=%s" % (PARAM_WIFI_PASSWD, wifi_info.get(PARAM_WIFI_PASSWD))
                if wifi_info.get(PARAM_WIFI_SECURITY) is not None:
                    params += " -o %s=%s" % (PARAM_WIFI_SECURITY, wifi_info.get(PARAM_WIFI_SECURITY))
            if dut_info.get(PARAM_BT_NAME) is not None:
                params += " -o %s=%s" % (PARAM_BT_NAME, dut_info.get(PARAM_BT_NAME))

        if self._enable_tcr:
            params += " --live_reporting %s --server_api_url %s --web_reporting_url %s" % \
                      (TCR_REPORT_LIB, TCR_REPORT_API_URL, TCR_REPORT_WEB_URL_PREFIX)

        if os.path.isfile(ACS_BIN):
            self.logger('Start to run ACS {} campaign.'.format(self._campaign))
            config_path = os.path.join(os.getcwd(), ACS_PACKAGE_PATH, "acs_test_suites")
            export_cmd = "export ACS_EXECUTION_CONFIG_PATH=%s" % config_path
            cmd = "%s && %s %s" % (export_cmd, ACS_BIN, params)
            if self._enable_tcr:
                proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                for line in iter(proc.stdout.readline, 'b'):
                    print line
                    if "TEST_REPORT_URL" in line:
                        url = line.split()[-1]
                        if url.startswith("http"):
                            self.logger('Test Report URL: {}'.format(url))
                    if proc.poll() is not None and line == "":
                        break
                proc.communicate()
                ret = proc.returncode
            else:
                ret = os.system(cmd)
            return ret
        else:
            raise Exception("ACS binary does not exist, stop testing.")

    def parse_test_result(self):
        """
        parse ACS log to get test result, like pass rate, execution rate
        """
        if not os.path.isdir(ACS_REPORTS_FOLDER):
            self.logger('{} folder does not exist.'.format(ACS_REPORTS_FOLDER))
            return

        log_list = []
        def list_files(folder, file_list):
            dir_list = os.listdir(folder)
            if not dir_list:
                return
            else:
                for f in dir_list:
                    f_path = os.path.join(folder, f)
                    if os.path.isdir(f_path):
                        list_files(f_path, file_list)
                    else: 
                        file_list.append(f_path)

        list_files(ACS_REPORTS_FOLDER, log_list)
        if not log_list:
            return

        log_list = sorted(log_list, key=lambda x : os.path.getctime(x))
        for f in reversed(log_list):
            if self._campaign in f and f.endswith('.log'):
                log_file = f
                break
        else:
            self.logger('{} campaign log does not exist.'.format(self._campaign))
            return

        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        not_executed_tests = 0
        log = open(log_file, 'r')
        for l in log.readlines():
            if "Tests Number" in l:
                total_tests = int(l.split('=')[-1].strip())
            if "Passed Number" in l:
                passed_tests = int(l.split('=')[-1].strip())
            if "Failed Number" in l:
                failed_tests = int(l.split('=')[-1].strip())
            if "Not Executed Number" in l:
                not_executed_tests = int(l.split('=')[-1].strip())
        self.logger('Pass rate: {0}/{1}'.format(passed_tests, total_tests))
        self.logger('Execution rate: {0}/{1}'.format(passed_tests + failed_tests, total_tests))

    def is_dut_alive(self):
        self.logger('Check DUT is alive...')
        self._adb_connection = ADB()
        if self._adb_connection.is_online():
            self.logger('DUT is alive.')
        else:
            self.logger('DUT is not alive.')

    def is_cpu_intel(self):
        self.logger('Check CPU is Intel...')
        if not self._adb_connection:
            self.logger('adb not connected, skip check')
            return
        model = self._adb_connection.shell('cat /proc/cpuinfo | grep "model name"')
        if model and 'Intel' in model:
            self.logger('There is Intel CPU on DUT.')
        else:
            self.logger('There is no Intel CPU on DUT, skip testing.')

    def main(self):
        exit_code = 1
        self.init_logger_file()
        try:
            self.is_dut_alive()
            self.is_cpu_intel()
            exit_code = self.run()
            self.parse_test_result()
        except Exception as e:
            self.logger(e)
        finally:
            self.share_logs()
            exit(exit_code)


def arg_parser():
    """
    parse command line arguments, return options and args
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('-c', '--campaign',
                        help='Campaign file to execute.',
                        metavar='TEST_CAMPAIGN',
                        dest='campaign_name',
                        required=True)

    parser.add_argument('--li', '--log_id',
                        help='Log ID used to define log file name.',
                        metavar='LOG ID',
                        dest='log_id')

    parser.add_argument('--enable_tcr',
                        help='Enable TCR living report.',
                        action='store_true',
                        dest='enable_tcr')

    return parser.parse_args()


# ------------------------------------------------------------------------------
if __name__ == "__main__":
    args = arg_parser()
    runner = runner(args)
    runner.main()
