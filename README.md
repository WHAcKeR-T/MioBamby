MioBamby is and admin dashboard website for e-commerce including MLM Affiliating features.
## Installation:
install python 3.11.5
install dependencies
commands:
```bash
virtualenv env
env\scripts\activate
```
(if u dont have access run this in powershell as admin: Set-ExecutionPolicy Unrestricted -Force)
```bash
pip install -r requirements.txt
python manage.py runserver
```
## Optional:
create a shortcut for the batch file and choose the icon from the static folder to run the server easier.

## Note:
change the gtk directory if it's needed inside accounts/views.py (os.add_dll_directory(r"C:\Program Files\GTK3-Runtime Win64\bin"))
