*** Test Cases ***
TC-AI-01 Test Case
    [Documentation]    Vérifie que l'utilisateur Ali peut s'authentifier avec succès
    [Tags]             ai-generated    ui    smoke
    Perform Login    ${ALI_LOGIN}    ${ALI_PASSWORD}
    Verify Welcome Page Is Displayed
    Verify Welcome Message Contains    Welcome back, ${ALI_FIRST_NAME}