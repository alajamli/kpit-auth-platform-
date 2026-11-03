TC-AI-01 Test Case
    [Documentation]    Verify that user Sara can successfully login and then logout from the application.
    [Tags]             ai-generated    ui    smoke    logout
    Perform Login    ${SARA_LOGIN}    ${SARA_PASSWORD}
    Verify Welcome Page Is Displayed
    Verify Welcome Message Contains    Welcome back, ${SARA_FIRST_NAME}
    Click Logout Button
    Verify Redirected To Login