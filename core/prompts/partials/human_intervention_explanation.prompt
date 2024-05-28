**IMPORTANT**
You must not tell me to run a command in the database or anything OS related - only if some dependencies need to be installed. If there is a need to run an OS related command, specifically tell me that this should be labeled as "Human Intervention" and explain what the human needs to do.
Avoid using "Human Intervention" if possible. You should NOT use "Human Intervention" for anything else than steps that you can't execute. Also, you must not use "Human Intervention" to ask user to test that the application works, because this will be done separately after all the steps are finished - no need to ask the user now.

Here are a few examples when and how to use "Human Intervention":
------------------------start_of_example_1---------------------------
Here is an example of good response for the situation where it seems like 3rd party API, in this case Facebook, is not working:

* "Human Intervention"
"1. Check latest Facebook API documentation for updates on endpoints, parameters, or authentication.
2. Verify Facebook API key/authentication and request format to ensure they are current and correctly implemented.
3. Use REST client tools like Postman or cURL to directly test the Facebook API endpoints.
4. Check the Facebook API's status page for any reported downtime or service issues.
5. Try calling the Facebook API from a different environment to isolate the issue."
------------------------end_of_example_1---------------------------

------------------------start_of_example_2---------------------------
Here is an example of good response for the situation where the user needs to enable some settings in their Gmail account:

* "Human Intervention"
"To enable sending emails from your Node.js app via your Gmail, account, you need to do the following:
1. Log in to your Gmail account.
2. Go to 'Manage your Google Account' > Security.
3. Scroll down to 'Less secure app access' and turn it on.
4. Under 'Signing in to Google', select 'App Passwords'. (You may need to sign in again)
5. At the bottom, click 'Select app' and choose the app you’re using.
6. Click 'Generate'.
Then, use your gmail address and the password generated in the step #6 and put it into the .env file."
------------------------end_of_example_2---------------------------

------------------------start_of_example_3---------------------------
Here is an example when there are issues with writing to the MongoDB connection:

* "Human Intervention"
"1. Verify the MongoDB credentials provided have write permissions, not just read-only access.
2. Confirm correct database and collection names are used when connecting to database.
3. Update credentials if necessary to include insert document permissions."
------------------------end_of_example_3---------------------------
