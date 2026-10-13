*** Settings ***
Documentation     基础登录流程（验证一对一映射）
Library           SeleniumLibrary    timeout=15    implicit_wait=3
Suite Setup       Open Browser    https://example.com    chrome
Suite Teardown    Close All Browsers

*** Variables ***
${USER}           id=username
${PWD}            id=password
${LOGIN_BTN}      id=login-btn

*** Test Cases ***
用户登录成功
    Go To    https://example.com/login
    Input Text    ${USER}    admin
    Input Password    ${PWD}    secret123
    Click Button    ${LOGIN_BTN}
    Wait Until Page Contains    欢迎回来    10s
    Title Should Be    个人中心
    Location Should Be    https://example.com/home
    Element Should Be Visible    css=.avatar
    Checkbox Should Be Selected    id=remember
    Capture Page Screenshot    login_ok.png

用户登出
    Click Element    css=.logout
    Page Should Not Contain    欢迎回来
    Title Should Be    登录页
