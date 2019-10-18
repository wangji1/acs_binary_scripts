import os
import sys
import setuptools
import subprocess
import tarfile
import argparse
from distutils.core import setup
from Cython.Build import cythonize
from distutils.extension import Extension
from datetime import date

REPO_NAME = 'acs_bin_package'
TAR_NAME = 'acs_bin_package.tar.gz'
EXCLUDE = ['.git', '.git-hooks', '.gitignore', 'CONTRIBUTING.md', 'README.md', '_Reports', 'docs', 'acs_setup_manager', 'acs_test_suites/ACS_CI']

def remove_exclude():
    for f in EXCLUDE:
        try:
            f_path = os.path.join(REPO_NAME, f)
            os.system('rm -rf {}'.format(f_path))
        except:
            raise


def get_all_py_files(root_path, file_list):
    # take root path as real path
    files = os.listdir(root_path)
    # change current working directory
    for f in files:
        f_path = os.path.join(root_path, f)
        if os.path.isfile(f_path) and f.endswith('.py') and "__init__.py" not in f:
            file_list.append(f_path)
        elif os.path.isdir(f_path):
            get_all_py_files(f_path, file_list)

def get_relative_path(f_path, root_path):
    return f_path[len(root_path):].strip('/')

def get_module_name(rel_path):
    modules = rel_path[:-3].split('/')
    return '.'.join(modules)

def build_standalone_executable(f_path):
    bin_path = f_path[:-3]
    c_path = bin_path + ".c"
    p = subprocess.Popen("cython {0} --embed -2".format(f_path), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = p.communicate()
    print stdout, stderr
    os.system("gcc -o {0} {1} -I /usr/include/python2.7 -lpython2.7".format(bin_path, c_path))

def build(root_path, repo_name):
    py_files = []
    get_all_py_files(os.path.join(root_path, repo_name), py_files)
    extensions = []
    so = []
    embed = []
    for f in py_files:
        if f.split('/')[-1] == 'ACS.py':
            embed.append(f)
        # need to change working dir, and build testlib separately
        elif 'OTC/libs/testlib' in f:
            pass
        elif 'tests' in f.split('/')[-2]:
            embed.append(f)
        else:
            so.append(f)
            relative_path = get_relative_path(f, root_path)
            module_name = get_module_name(relative_path)
            e = Extension(module_name, [relative_path])
            extensions.append(e)
    # build so files and remove .py .pyc files
    try:
        setup(ext_modules = cythonize(extensions, gdb_debug=True, compiler_directives={'language_level' : "2", 'always_allow_keywords': True}),script_args=["build_ext", "-b", root_path])
    except Exception, ex:
        print "build error! ", ex.message
    finally:
        for f in so:
            # remove .py files
            os.system("rm {}".format(f))
            f += 'c'
            if os.path.exists(f):
                os.system("rm {}".format(f))
    
    # build embed main binary, and remove .py .c files
    for f in embed:
        build_standalone_executable(f)
        os.system('rm ' + f)
        c_file = f[:-2] + "c"
        os.system('rm ' + c_file)

def build_testlib(root_path):
    cwd = os.getcwd()
    os.chdir(root_path)
    build("./", "testlib")

def export_git_commit():
    cwd = os.getcwd()
    os.chdir(REPO_NAME)
    os.system('git log | head -n 20 > last_commit')
    os.chdir(cwd)

if __name__ == '__main__':
    # parse argument
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path', help='specify the acs code path', required=True)
    parser.add_argument('-o', '--output', help='specify the output path', required=True)
    parser.add_argument('-c', '--compress', help='bool, -c True, will compress the output as tar.gz')
    parser.add_argument('-g', '--git_commit', help='bool, -g True, will export last commit info of git')
    parser.add_argument('-k', '--key', help='provide the API key to upload package to artifactory')
    args = parser.parse_args()
    
    cwd = os.getcwd()

    original_repo = os.path.join(cwd, args.path)
    if not os.path.exists(original_repo):
        exit("{} not found".format(original_repo))
    working_path = os.path.realpath(os.path.join(cwd, args.output))
    working_repo = os.path.realpath(os.path.join(working_path, REPO_NAME))
    if os.path.exists(working_repo):
        exit("output path {} exists, please remove and try again".format(working_repo))
    os.system('cp -r {} {}'.format(original_repo, working_repo))
    os.chdir(working_path)

    if args.git_commit:
        export_git_commit()

    remove_exclude()

    build(working_path, REPO_NAME)
    testlib_path = os.path.join(working_repo, "acs_test_suites", "OTC", "libs")
    build_testlib(testlib_path)
    output = os.path.join(working_path, REPO_NAME)
    os.chdir(working_path)
    if args.compress:
        print "start compressing"
        tar_path = os.path.join(working_path, TAR_NAME)
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(REPO_NAME)

    if args.key:
        print "start uploading to artifactory"
        curl_cmd = """ curl -H 'X-JFrog-Art-Api:{}' -T  ./acs_bin_package.tar.gz  "https://mcg-depot.intel.com/artifactory/acs_test_artifacts/OTC_Android_Auto_Test_Suite/resources/acs_bin_package.tar.gz" --insecure """.format(args.key)
        os.system(curl_cmd)
        curl_cmd = """ curl -H 'X-JFrog-Art-Api:{}' -T  ./acs_bin_package.tar.gz  "https://mcg-depot.intel.com/artifactory/acs_test_artifacts/openTaaS/acs_binary/acs_bin_package_{}.tar.gz" --insecure """.format(args.key, date.today().strftime("%d_%m_%Y"))
        os.system(curl_cmd)
    
    os.chdir(cwd)




