    # init CLI
    # 1. show the type of the app that needs to be created
    # 1.c ask user to press enter if it's ok, or to add the type of the app they want
        # if it's not ok, check if the wanted app CAN be created
            # if it can, print confirmation message and continue
            # if it can't, print error message and exit
    # 2. ask user for the main definition of the app
    # start the processing queue


# 2. show the user flow of the app
# 2.c ask user to press enter if it's ok, or to add the user flow they want
    # ask for input until they just press enter
    # recompute the user flow and ask again
# 3. show the COMPONENTS of the app
    # 3.1 frontend
    # 3.2 backend
    # 3.3 database
    # 3.4 config
    # 3.x ask user to press enter if it's ok, or to add the components they want
        # ask for input until they just press enter
        # recompute the components and ask again
# 4. break down the FILES that need to be created to support each of the components
    # ask user to press enter if it's ok, or to add the files they want
        # ask for input until they just press enter
        # recompute the files and ask again
# 5. loop through components (IMPORTANT!!!)
    # 5.1 loop through use cases
        # 5.1.1 for each case in each component, break down the files, functions and dependencies that need to be created
            # each function will have a description
            # in each loop, we will send all the previous files and functions so that LLM can change them if needed
# 6. break down the tests that need to be created
    # in the prompt, send all the files and functions
    # start from the high level tests and go down to the unit tests
    # 6.1 ask user to press enter if it's ok, or to add the tests they want
        # ask for input until they just press enter
        # recompute the tests and ask again
# 7. write the tests
# 8. write the files for each test
# 9. run each created test once the code is written
    # start from low level tests and do the high level tests last
    # track which test is related to which code
    # GPT should first say which functions will it use for a test and then we check if any of those functions is already written and if so, we send it to LLM to change it
    # track code coverage and increase to get to 100%
    # if the code requires something from config, ask the user to add it
    # if the code requires
    # when files overlap, ask LLM to combine them
# 10. try debugging 5 times
    # 10.1 if it doesn't work, ask the user to debug (!!!IMPORTANT!!!)
        # show them the explanations
        # ask for input if they want to enter something and retry 5 debugging attempts
# 11. create build/run script
# 12. RUN THE APP


# 4. show the components of the app setup
    # a. installation process
    # b. configuration process
    # c. running process
    # d. building process
    # e. testing process


# comments
# 1. Možemo koristiti dodatni model koji će izvlačiti iz GPT responsea što treba pokrenuti, što treba updateati, koji komentar složiti, etc. - da ne trebamo i to učiti originalni model in context
