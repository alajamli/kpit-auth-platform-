*** Test Cases ***
ahmedynajemylgini
    [Documentation]    Vérifie que Ahmed peut se connecter avec succès à la plateforme KPIT Auth.
    [Tags]             ai-generated    ui    smoke
    Perform Login    ${AHMED_LOGIN}    ${AHMED_PASSWORD}
    Verify Welcome Page Is Displayed
    Verify Welcome Message Contains    Welcome back, ${AHMED_FIRST_NAME}