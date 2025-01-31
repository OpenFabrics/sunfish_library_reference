#!bash
set -e 
cd ~/utils_resources
cp -rp * ~/playpen_base/test_SC24/server_start_Resources
cp -rp * ~/playpen_base/test_SC24/sc24_sunfish_server/Resources
gnome-terminal --tab --title="Sunfish" --command="bash -c 'cd ~/playpen_base/test_SC24/sc24_sunfish_server; . venv/bin/activate; flask run -p 5000 --debugger;$BASH'"
