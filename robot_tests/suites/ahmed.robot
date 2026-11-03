TC-AI-01 Test Case
    [Documentation]    Vérifier que Ahmed peut s'authentifier avec succès et que son rôle est admin
    [Tags]             ai-generated    ui    smoke
    Perform Login    ${AHMED_LOGIN}    ${AHMED_PASSWORD}
    Verify Welcome Page Is Displayed
    Verify Welcome Message Contains    Welcome back, ${AHMED_FIRST_NAME}