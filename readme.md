# MIGRATIONS 
STEP 1 : pip install Flask-Migrate
STEP 2 : flask db init
STEP 3 : flask db migrate -m "add org ladder"
STEP 4 : flask db upgrade



# How to create and requirements.txt file
python -m pip freeze > requirements.txt

# How to install from requirements.txt
pip install -r requirements.txt


# How to create an offline folder of python packages
mkdir offline_packages
pip download -r requirements.txt -d offline_packages


# Installing these packages without internet
pip install --no-index --find-links=offline_packages -r requirements.txt