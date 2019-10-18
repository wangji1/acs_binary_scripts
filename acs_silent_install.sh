#!/bin/bash
##########################################################
# Copyright (C) 2018 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions
# and limitations under the License.
#
#
# SPDX-License-Identifier: Apache-2.0
###########################################################

echo Start dependencies installation
echo `date +"%Y-%m-%d %H:%M:%S"`

if [ $(id -u) -ne 0 ]; then
  echo "Unable to install: you must run this script as root"
  exit 1
fi

is_python_supported()
{
  V1=2
  V2=7
  PY_V1=`python -V 2>&1|awk '{print $2}'|awk -F '.' '{print $1}'`
  PY_V2=`python -V 2>&1|awk '{print $2}'|awk -F '.' '{print $2}'`
  if [[ $PY_V1 -eq $V1 && $PY_V2 -eq $V2 ]]; then
    return 0
  else
    return 1
  fi
}

python --version
if [ $? -ne 0 ]; then
  echo Please install a supported python version 2.7.x
  exit 1
else
  py_support=`is_python_supported`
  if [[ $py_support -ne 0 ]]; then
    echo Please install a supported python version 2.7.x
    exit 1
  fi
fi

echo installing pip ...
apt-get update -y
apt-get install python-pip -y
if [ $? -ne 0 ]; then
  echo Error during install
  exit 1
fi

echo installing python libraries ...
is_pip_install_succeed=0
pip install -U pip
cd "$(dirname "$0")"
for i in `seq 1 3`
do
  pip install -r ./pip_requirements.txt
  if [ $? -eq 0 ]; then
    is_pip_install_succeed=1
    echo Successfully to install requirements through pip
    break
  fi
done
if [ $is_pip_install_succeed -eq 0 ]; then
  echo Error during pip install
  exit 1
fi

echo installing tools for build ffmpeg
apt-get install -y automake autoconf libtool gcc g++ build-essential checkinstall \
libopencore-amrwb-dev libtheora-dev libvdpau-dev libvorbis-dev libxvidcore-dev lame \
libva-dev libvpx-dev yasm zlib1g-dev libx264-dev librtmp-dev libfdk-aac-dev fdkaac git
if [ $? -ne 0 ]; then
  echo Error during install
  exit 1
fi

#basepath=$(cd `dirname $0`; pwd)
#toolsdir=$basepath/
echo download ffmpeg and x264 packages
mkdir -p tools && cd tools
git clone https://git.ffmpeg.org/ffmpeg.git
git clone https://git.videolan.org/git/x264.git

echo build x264
cd x264
./configure --enable-shared --enable-static --disable-asm --prefix=/usr/local
make
make install
ldconfig

echo build ffmpeg
cd ../ffmpeg
./configure --prefix=/usr/local --enable-libx264 --enable-libfdk-aac --enable-libvpx --enable-libvorbis --enable-shared --enable-gpl --enable-version3 --enable-nonfree
make
make install
ldconfig

echo remove tools
cd ../../
rm -rf tools

echo installing adb tool
if [ -x /usr/bin/adb ]; then
  echo adb already exists
else
  apt-get install -y android-tools-adb
  if [ $? -ne 0 ]; then
    echo Error during install
    exit 1
  fi
  echo -e "# Intel vendor ID for ADB\nSUBSYSTEM==\"usb\", ATTRS{idVendor}==\"8087\", MODE=\"0666\"" > 51-android.rules
  mv 51-android.rules /etc/udev/rules.d/
  echo restart udev rules
  service udev restart
fi

echo `date +"%Y-%m-%d %H:%M:%S"`
echo End installation
