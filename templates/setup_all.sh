#!/bin/bash
# Copyright (c) 2018-2023, The Storage Networking Industry Association.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# Neither the name of The Storage Networking Industry Association (SNIA) nor
# the names of its contributors may be used to endorse or promote products
# derived from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#  AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
#  ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
#  LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#  CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
#  SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
#  INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
#  CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
#  ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
#  THE POSSIBILITY OF SUCH DAMAGE.

# exit on error
set -e 

BASE_DIR=$(pwd)
WORK_DIR=$BASE_DIR/test_SC24
API_PORT=5000
SETUP_ONLY=

EXTFILE=certificate_config.cnf

print_help() {
    cat <<EOF

Helper to set up a Sunfish + 2 Agents emulator. This will take care of getting the
    'Sunfish core library' repo downloaded from the sunfish_library_reference and built
    'Sunfish Services' API built server from the sunfish_reference_server and linked to the Sunfish Core Lib
    'Fabric Manager' agent built from the sunfish_reference_server and linked to the Sunfish Core Lib
    'Appliance manager' agent built from the sunfish_reference_server and linked to the Sunfish Core Lib

USAGE:

    $(basename $0) [--port PORT] [--workspace DIR] 

Options:

    -p | --port PORT     -- Port to run the emulator on. Default is $API_PORT.

    -w | --workspace DIR -- Directory to set up the emulator. Defaults to
                            '$WORK_DIR'.


EOF
}

# Extract command line args
while [ "$1" != "" ]; do
    case $1 in
        -p | --port )
            shift
            API_PORT=$1
            ;;
        -w | --workspace )
            shift
            WORK_DIR=$1
            ;;
        -n | --no-start)
            SETUP_ONLY="true"
            ;;
        *)
            print_help
            exit 1
    esac
    shift
done

# Do some system sanity checks first
if ! [ -x "$(command -v python3)" ]; then
    echo "Error: python3 is required to run the emulator and executable not" \
         "found"
    echo ""
    echo "See https://www.python.org/downloads/ for installation instructions."
    echo ""
    exit 1
fi

if ! [ -x "$(command -v virtualenv)" ]; then
    echo "Error: virtualenv is required."
    echo ""
    echo "See https://virtualenv.pypa.io/en/stable/installation/ for" \
         "installation instructions."
    echo ""
    exit 1
fi

if ! [ -x "$(command -v git)" ]; then
    echo "Error: git is required."
    echo ""
    echo "See https://git-scm.com/book/en/v2/Getting-Started-Installing-Git" \
         "for installation instructions."
    echo ""
    exit 1
fi


echo "Creating workspace: '$WORK_DIR'..."
rm -fr $WORK_DIR
mkdir $WORK_DIR
mkdir $WORK_DIR/mockups
mkdir $WORK_DIR/am_agent_Resources
mkdir $WORK_DIR/fm_agent_Resources
mkdir $WORK_DIR/server_start_Resources
mkdir $WORK_DIR/sc24_sunfish_lib
mkdir $WORK_DIR/sc24_sunfish_server
mkdir $WORK_DIR/sc24_appliance_manager
mkdir $WORK_DIR/sc24_fabric_manager

cd $WORK_DIR/mockups
# Get the mockups
echo "Getting CXL mockups repo at github.com:OFMFWG/mockups ..."
git clone git@github.com:OFMFWG/mockups.git .
# switch to the right branch
git switch sc23-CXL-Poc-Russ
# cd to the desired mockups tree --(sc24-PoC)
cd ./sc24-PoC
# copy the appropriate sc24-PoC resource directory trees to 
# where the various API servers will look for their startup mockup resources
cd ./am_agent_Resources/
cp -rp * $WORK_DIR/am_agent_Resources/
cd ../fm_agent_Resources/
cp -rp * $WORK_DIR/fm_agent_Resources/
cd ../server_start_Resources/
cp -rp * $WORK_DIR/server_start_Resources/


# Get and build Sunfish library core
echo "Getting Sunfish Library  ..."
cd $WORK_DIR/sc24_sunfish_lib
git clone git@github.com:OpenFabrics/sunfish_library_reference.git .
git switch rwh_CXL_Agent_fabric_merge
virtualenv venv
. venv/bin/activate
pip3 install -r requirements.txt
make build
deactivate

# Get the Sunfish Server and build it
echo "Getting Sunfish Server  ..."
# First get the sunfish_server
cd $WORK_DIR/sc24_sunfish_server
git clone git@github.com:OpenFabrics/sunfish_server_reference.git .
git switch rherrell_fix_8_9_10
virtualenv venv
. venv/bin/activate
pip3 install -r requirements.txt
# install the library core we just built into the sunfish server venv
pip3 install --force-reinstall ../sc24_sunfish_lib/dist/sunfish-0.1.0-py3-none-any.whl
# now customize the generic sunfish_server by using the correct app.py file
cp app_sunfish_server.py app.py
deactivate

# Get the fabric manager server and build it
echo "Getting Fabric Manager Server  ..."
cd $WORK_DIR/sc24_fabric_manager
# First get the sunfish_server
git clone git@github.com:OpenFabrics/sunfish_server_reference.git .
git switch rherrell_fix_8_9_10
virtualenv venv
. venv/bin/activate
pip3 install -r requirements.txt
# install the library core into the fabric manager server
pip3 install --force-reinstall ../sc24_sunfish_lib/dist/sunfish-0.1.0-py3-none-any.whl
# now customize the generic sunfish_server by using the correct app.py file
cp app_fabric_mgr.py app.py
deactivate

# Get the appliance manager server and build it
echo "Getting Appliance Manager Server  ..."
cd $WORK_DIR/sc24_appliance_manager
# First get the sunfish_server
git clone git@github.com:OpenFabrics/sunfish_server_reference.git .
git switch rherrell_fix_8_9_10
virtualenv venv
. venv/bin/activate
pip3 install -r requirements.txt
# install the library core into the appliance_manager server
pip3 install --force-reinstall ../sc24_sunfish_lib/dist/sunfish-0.1.0-py3-none-any.whl
# now customize the generic sunfish_server by using the correct app.py file
cp app_appliance_mgr.py app.py
deactivate
cd $WORK_DIR


echo ""
echo "demo can be launched with"
echo "cd $BASE_DIR; sh ./quick_start.sh"
echo ""
echo "which will fire up the Sunfish API server"
echo "and two instances of Agents"
echo ""
echo "Then 'cd $WORK_DIR/sc24_appliance_manager/templates' and"
echo "use the shell scripts found there to reset the demo"

exit 0
