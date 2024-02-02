# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License.
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE

all:  build

build: 
	poetry build

test:
	python3 -m pytest tests/test_sunfishcore_library.py -vvvv

clean:
	rm -r dist


