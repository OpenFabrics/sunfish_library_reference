#!bash
set -e 
gnome-terminal --tab --title="Sunfish" --command="bash -c 'cd ~/post_dev/try_main/test_SC24/sc24_sunfish_server; . venv/bin/activate; flask run -p 5000 --debugger;$BASH'"
gnome-terminal --tab --title="Fabric Mgr" --command="bash -c 'cd ~/post_dev/try_main/test_SC24/sc24_fabric_manager; . venv/bin/activate; flask run -p 5001 --debugger;$BASH'"
gnome-terminal --tab --title="Appliance Mgr" --command="bash -c 'cd ~/post_dev/try_main/test_SC24/sc24_appliance_manager; . venv/bin/activate; flask run -p 5002 --debugger;$BASH'"
