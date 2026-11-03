*** Settings ***
Documentation    Generated Test Suite
Library          SeleniumLibrary
Test Setup       Open Browser    ${URL}    ${BROWSER}
Test Teardown    Close Browser

*** Variables ***
${BROWSER}       headlesschrome
${URL}           https://www.saucedemo.com
${USERNAME}      standard_user
${PASSWORD}      secret_sauce

*** Test Cases ***
TC-AI-01 Test Case
    [Documentation]  Authenticate user and verify product catalog is displayed
    [Tags]           UI    Generated
    Wait Until Page Contains Element    id=user-name    timeout=10s
    Input Text    id=user-name    ${USERNAME}
    Input Text    id=password    ${PASSWORD}
    Click Element    id=login-button
    Wait Until Page Contains    Products    timeout=10s
    Wait Until Page Contains Element    css=.title    timeout=10s
    Should Contain    ${PAGE SOURCE}    Products