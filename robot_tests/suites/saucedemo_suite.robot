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
TC-AI-01 Test login
    [Documentation]  Test the login functionality on SauceDemo using standard_user and secret_sauce. Verify that after clicking the login button, the user is redirected to the products page (title 'Products'). Next, add the 'Sauce Labs Backpack' to the cart, navigate to the shopping cart page, and verify that the item is present in the cart.
    [Tags]           UI    Generated
    Wait Until Page Contains Element    id=user-name    timeout=10s
    Input Text    id=user-name    ${USERNAME}
    Input Text    id=password    ${PASSWORD}
    Click Element    id=login-button
    Wait Until Page Contains    Products    timeout=10s
    Wait Until Page Contains Element    id=add-to-cart-sauce-labs-backpack    timeout=10s
    Click Element    id=add-to-cart-sauce-labs-backpack
    Wait Until Page Contains Element    css=.shopping_cart_link    timeout=10s
    Click Element    css=.shopping_cart_link
    Wait Until Page Contains Element    css=.inventory_item_name    timeout=10s
    Wait Until Page Contains    Sauce Labs Backpack    timeout=10s