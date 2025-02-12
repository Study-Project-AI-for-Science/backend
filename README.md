# Backend
## !Tested only on Mac! <br>

### Database Startup
To spin up the database for local testing follow the following steps:
1. Install [docker](https://docs.docker.com/engine/install/)
2. install the pip requirements using `pip install -r requirements.txt`
3. run `chmod +x ./scripts/setup.sh && ./scripts/setup.sh` 
4. Profit
<br>
If you want to also insert a few sample files to the database as well as the s3 storage, you can insted replace step three with the following:
3. run `chmod +x ./setup_with_samples.sh && ./setup_with_samples.sh`

If everthing worked as intended, the postgressql database and the s3 storage are now running and ready to be worked with


### Delete database and volumes

Sometimes, maybe if something goes wrong, you want to test something, or for some other reason, you want to delete the database and start with a clean one, simply follow the following steps:
1. stop and delete the running docker containers (in the dashboard using docker desktop simply click on the bin for the aiforscience docker compose) 
2. Delete the volumes folder
3. Run one of the setup scripts and afterwards you are good to go again