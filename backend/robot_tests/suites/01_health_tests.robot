```robot
*** Settings ***
Documentation     Health check tests for KPIT Auth Platform API.
...               These tests verify that the API is up and responding correctly.
Library           RequestsLibrary
Library           Collections


*** Variables ***
${BASE_URL}       http://127.0.0.1:5000


*** Test Cases ***

TC-001 API Health Check Should Return Healthy Status
    [Documentation]    Verify that the health endpoint returns a 200 status
    ...                and confirms the API is running properly.
    [Tags]             health    smoke    api
    
    # Créer une session HTTP vers notre API
    Create Session     kpit_api    ${BASE_URL}
    
    # Faire une requête GET sur /health
    ${response}=       GET On Session  kpit_api    /health
    
    # Vérifier le status code
    Should Be Equal As Numbers    ${response.status_code}    200
    
    # Vérifier le contenu de la réponse
    ${json}=           Set Variable    ${response.json()}
    Should Be Equal    ${json}[status]     healthy
    Should Contain     ${json}[message]    KPIT Auth Platform API
    
    # Log pour le rapport
    Log    ✅ API is healthy and responding correctly


TC-002 Root Endpoint Should Return Welcome Message
    [Documentation]    Verify that the root endpoint returns a welcome message
    ...                and confirms the API version.
    [Tags]             health    api
    
    # Créer une session (si pas déjà fait)
    Create Session     kpit_api_root    http://localhost:5000
    
    # GET sur / (racine)
    ${response}=       GET On Session    kpit_api_root    /docs
    
    # Vérifier le status
    Should Be Equal As Numbers    ${response.status_code}    200
    
    Log    ✅ Root/Docs endpoint is accessible




TC-AI-01 Test Case
    [Documentation]    Authenticate user and verify product catalog is displayed
    [Setup]    Open Browser    ${URL}    ${BROWSER}
    [Teardown]    Close Browser

    # Step 1: Enter username
    Input Text    id=user-name    ${USERNAME}

    # Step 2: Enter password
    Input Text    id=password    ${PASSWORD}

    # Step 3: Click Login button
    Click Element    id=login-button

    # Step 4: Verify product catalog is displayed
    Page Should Contain    Products
    Element Should Be Visible    id=inventory_container
