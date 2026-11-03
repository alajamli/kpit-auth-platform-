TC-AI-01 Test Case
    [Documentation]    Vérifie que l'utilisateur Ahmed peut se connecter avec succès à la plateforme.
    [Tags]             ai-generated    ui    smoke
    Perform Login    ${AHMED_LOGIN}    ${AHMED_PASSWORD}
    Verify Welcome Page Is Displayed
    Verify Welcome Message Contains    Welcome back, ${AHMED_FIRST_NAME}