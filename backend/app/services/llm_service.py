"""
Service LLM (Groq / Llama 3) - KPIT Auth Platform.

Génère des scripts de test Robot Framework :
1. Soit pour la suite interne KPIT (03_ui_tests.robot / 01_api_tests.robot)
2. Soit de manière générique et dynamique pour n'importe quel site web client externe (target_url)
"""
import os
import re
import json
import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

# =====================================================================
# OFFICIAL PROMPTS
# =====================================================================

SYSTEM_PROMPT_UI = """Vous êtes un expert Robot Framework pour l'application Web KPIT Auth Platform (suite '03_ui_tests.robot').

CHAQUE CAS DE TEST DOIT OBLIGATOIREMENT CONTENIR LES EN-TÊTES :
- [Documentation]    Description claire du test
- [Tags]             ai-generated    ui    <tag_spécifique>

INSTRUCTIONS STRICTES SELON LE TYPE DE TEST :

1. TEST D'ÉCHEC / ERREUR DE CONNEXION (si la demande contient: "échec", "fail", "mauvais", "wrong", "invalide", "erreur") :
   - Utilisez Perform Login avec un mauvais mot de passe (ex: WrongPass123).
   - Vérifiez le message d'erreur : Verify Error Message Is Displayed    Invalid username or password
   - Tags : [Tags]    ai-generated    ui    security    error
   - Ne JAMAIS inclure "Verify Welcome Page Is Displayed" dans un test d'échec !

2. TEST DE CONNEXION RÉUSSIE :
   - Perform Login    <username>    <password>
   - Verify Welcome Page Is Displayed
   - Verify Welcome Message Contains    Welcome back, <FIRST_NAME>
   - Tags : [Tags]    ai-generated    ui    smoke

3. TEST DE DÉCONNEXION (logout) :
   - Click Logout Button
   - Verify Redirected To Login
   - Tags : [Tags]    ai-generated    ui    logout

MOTS-CLÉS UI VALIDES (UTILISER EXCLUSIVEMENT CEUX-CI) :
- Perform Login    <username>    <password>    (EXACTEMENT 2 ARGUMENTS)
- Verify Welcome Page Is Displayed
- Verify Welcome Message Contains    Welcome back, <FIRST_NAME>
- Verify Error Message Is Displayed    Invalid username or password
- Click Logout Button
- Verify Redirected To Login

COMPTES UTILISATEURS :
- Sara  : ${SARA_LOGIN} / ${SARA_PASSWORD} / ${SARA_FIRST_NAME}
- Ahmed : ${AHMED_LOGIN} / ${AHMED_PASSWORD} / ${AHMED_FIRST_NAME}
- Ali   : ${ALI_LOGIN} / ${ALI_PASSWORD} / ${ALI_FIRST_NAME}

STRUCTURE STRICTE D'UN CAS DE TEST :
<Test_Case_Name>
    [Documentation]    <description>
    [Tags]             ai-generated    ui
    <Keywords>
"""

SYSTEM_PROMPT_API = """Vous êtes un expert Robot Framework pour l'API REST KPIT Auth Platform.

CHAQUE CAS DE TEST DOIT OBLIGATOIREMENT CONTENIR :
- [Documentation]    Description du test API
- [Tags]             ai-generated    api    <tag_spécifique>

INSTRUCTIONS STRICTES SELON LE TYPE DE TEST :

1. TEST DE CONNEXION RÉUSSIE :
   - Create API Session
   - Login Should Succeed    <login>    <password>
   - Tags : [Tags]    ai-generated    api    login_success
   - (ATTENTION : 'Login Should Succeed' effectue déjà toutes les vérifications. Ne JAMAIS ajouter 'Verify Response Is Success ${response}' !)

2. TEST D'ÉCHEC DE CONNEXION / ERREUR :
   - Create API Session
   - Login Should Fail With Unauthorized    <login>    <password>
   - Tags : [Tags]    ai-generated    api    login_failure

3. INSCRIPTION D'UN NOUVEL UTILISATEUR :
   - Create API Session
   - Register New User With Random Data
   - Tags : [Tags]    ai-generated    api    register

MOTS-CLÉS API OFFICIELS (UTILISER EXCLUSIVEMENT CEUX-CI) :
- Create API Session
- Register New User With Random Data
- Login Should Succeed    <login>    <password>
- Login Should Fail With Unauthorized    <login>    <password>

VARIABLES COMPTES UTILISATEURS :
- Ahmed : ${AHMED_LOGIN} / ${AHMED_PASSWORD} / ${AHMED_EMAIL}
- Sara  : ${SARA_LOGIN} / ${SARA_PASSWORD} / ${SARA_EMAIL}
- Ali   : ${ALI_LOGIN} / ${ALI_PASSWORD} / ${ALI_EMAIL}

STRUCTURE STRICTE D'UN CAS DE TEST :
<Test_Case_Name>
    [Documentation]    <description>
    [Tags]             ai-generated    api
    <Keywords>
"""

SYSTEM_PROMPT_GENERIC = """You are an expert Robot Framework QA Automation Engineer.
Your task is to generate complete, executable Robot Framework (.robot) test scripts using SeleniumLibrary for web applications.

CRITICAL MANDATORY RULES FOR GENERATION:
1. Direct Robot Framework Syntax ONLY: Output ONLY pure Robot Framework code. Do NOT wrap inside ```robot markdown blocks. Do NOT include conversation or explanations.

2. MANDATORY BROWSER SETUP & TEARDOWN:
   - You MUST open the browser before performing actions! Put `Test Setup    Open Browser    ${URL}    ${BROWSER}` in *** Settings *** OR make the very first line of the test case `Open Browser    ${URL}    ${BROWSER}`.
   - You MUST close the browser! Put `Test Teardown    Close Browser` in *** Settings *** or `[Teardown]    Close Browser` at the end of the test case.

3. STRICT VARIABLE NAME MATCHING (CRITICAL):
   - Every variable defined in *** Variables *** MUST be used with the EXACT SAME NAME in *** Test Cases ***.
   - If you define `${PASSWORD}    secret_sauce` in *** Variables ***, you MUST write `${PASSWORD}` in *** Test Cases ***. NEVER write `${PASSWD}`, `${PASS}`, or `${password}`.
   - If you define `${USERNAME}    standard_user`, write `${USERNAME}` everywhere.

4. STRUCTURE REQUIREMENTS:
   *** Settings ***
   Documentation    Generated Test Suite
   Library          SeleniumLibrary
   Test Setup       Open Browser    ${URL}    ${BROWSER}
   Test Teardown    Close Browser

   *** Variables ***
   ${BROWSER}       headlesschrome
   ${URL}           <target_url>
   ${USERNAME}      <username>
   ${PASSWORD}      <password>

   *** Test Cases ***
   <Test_Name>
       [Documentation]  <requirement>
       [Tags]           UI    Generated
       <Steps with explicit Wait Until Page Contains / Wait Until Page Contains Element>

5. ACCURATE DOM LOCATORS:
   - For SauceDemo (https://www.saucedemo.com):
     * Username Field: id=user-name
     * Password Field: id=password
     * Login Button: id=login-button
     * Products Title: css=.title or text 'Products'
     * Add Sauce Labs Backpack to Cart: id=add-to-cart-sauce-labs-backpack
     * Shopping Cart Icon/Link: css=.shopping_cart_link
     * Cart Item Name: css=.inventory_item_name
   - Always use `Wait Until Page Contains Element` before interacting with dynamic elements.
"""


class LLMService:

    @classmethod
    def _get_available_models(cls, api_key: str) -> list:
        """Découvre dynamiquement les modèles textuels actifs sur Groq API."""
        default_active_models = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant"
        ]
        try:
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/models",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "Mozilla/5.0"
                }
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                discovered = []
                for m in data.get('data', []):
                    m_id = m.get('id', '')
                    if any(name in m_id.lower() for name in ['llama', 'mixtral', 'gemma', 'qwen']):
                        if not any(bad in m_id.lower() for bad in ['guard', 'whisper', 'safetensors', 'embed']):
                            discovered.append(m_id)

                if discovered:
                    logger.info(f"Groq active text models discovered: {discovered}")
                    return discovered
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode('utf-8', errors='ignore')
            logger.warning(f"Groq GET /models HTTP {e.code}: {err_msg}")
        except Exception as e:
            logger.warning(f"Could not fetch Groq models dynamically: {e}")

        return default_active_models

    @classmethod
    def _sanitize_and_fix_robot_code(cls, code: str, target_suite: str = "03_ui_tests.robot", requirement: str = "", target_url: str = None) -> str:
        """
        POST-PROCESSEUR AUTOMATIQUE (GUARDRAIL) :
        1. Nettoie le Markdown.
        2. Assure la présence de [Documentation] et [Tags].
        3. Corrige la syntaxe et les mots-clés pour la suite interne OU pour un site externe.
        """
        code = re.sub(r'```robotframework|```robot|```', '', code).strip()
        is_ui_suite = '03_ui' in target_suite or 'ui' in target_suite.lower()
        is_generic_external = bool(target_url and target_url.strip() and not is_ui_suite)

        lines = code.splitlines()
        cleaned_lines = []
        has_tags = False
        has_doc = False

        for line in lines:
            stripped = line.strip()

            if '[Tags]' in line:
                has_tags = True
            if '[Documentation]' in line:
                has_doc = True

            # Pour les tests internes KPIT Auth Platform UI
            if is_ui_suite and not is_generic_external:
                if any(stripped.startswith(cmd) for cmd in ["Open Browser", "Close Browser", "Maximize Browser Window", "[Teardown]  Close Browser", "[Teardown]    Close Browser"]):
                    continue

                line = re.sub(r'\bPerform Logout\b', 'Click Logout Button', line)
                line = re.sub(r'\bVerify Home Page Is Displayed\b', 'Verify Welcome Page Is Displayed', line)
                line = re.sub(r'\bVerify Dashboard Is Displayed\b', 'Verify Welcome Page Is Displayed', line)

                if 'Perform Login' in line:
                    parts = [p for p in re.split(r'\s{2,}', line.strip()) if p]
                    if len(parts) > 3:
                        line = f"    Perform Login    {parts[1]}    {parts[2]}"

            cleaned_lines.append(line)

        # INJECTION AUTOMATIQUE DE TAGS ET DOCUMENTATION SI MANQUANTS
        final_lines = []
        default_tag = "ui" if is_ui_suite else "generic"

        for line in cleaned_lines:
            final_lines.append(line)
            if line.strip() and not line.startswith(' ') and not line.startswith('\t') and not line.startswith('*') and not line.startswith('#'):
                if not has_doc:
                    doc_desc = requirement if requirement else "Test généré par IA"
                    final_lines.append(f"    [Documentation]    {doc_desc}")
                    has_doc = True
                if not has_tags:
                    final_lines.append(f"    [Tags]             ai-generated    {default_tag}    auto")
                    has_tags = True

        final_code = "\n".join(final_lines)

        # Nettoyage spécifique aux tests internes
        if is_ui_suite and not is_generic_external:
            final_code = re.sub(
                r'(Click Logout Button\n\s*Verify Redirected To Login)\n\s*Verify Welcome Page Is Displayed',
                r'\1',
                final_code
            )
            if 'Verify Error Message Is Displayed' in final_code:
                res_lines = []
                for l in final_code.splitlines():
                    if 'Verify Welcome Page Is Displayed' in l or 'Verify Welcome Message Contains' in l:
                        continue
                    res_lines.append(l)
                final_code = "\n".join(res_lines)

        # Forçage du mode Headless Chrome pour les tests externes cibles
        if is_generic_external and "Open Browser" in final_code and "headlesschrome" not in final_code.lower():
            final_code = re.sub(
                r'(Open Browser\s+[^\s]+\s+)(\w+)',
                r'\1headlesschrome',
                final_code
            )

        return final_code

    @classmethod
    def generate_robot_test(
        cls,
        requirement: str,
        test_name: str = "TC-AI Generated Test",
        target_suite: str = "03_ui_tests.robot",
        target_url: str = None,
        test_data: str = None
    ) -> dict:
        """
        Génère un cas de test Robot Framework via l'API Groq LLM.
        Supporte les prompts internes KPIT et les URLs externes cibles.
        """
        requirement = (requirement or "").strip()
        test_name = (test_name or "TC-AI Generated Test").strip()
        target_suite = (target_suite or "03_ui_tests.robot").strip()
        target_url_clean = (target_url or "").strip()
        test_data_clean = (test_data or "").strip()

        if not requirement:
            return {"status": "error", "message": "Requirement is empty", "code": ""}

        # 1. Sélection du prompt selon présence d'URL externe
        if target_url_clean:
            system_prompt = SYSTEM_PROMPT_GENERIC
            user_prompt = (
                "Target Web Application URL: " + target_url_clean + "\n"
                "Test Credentials / Parameters: " + (test_data_clean if test_data_clean else "None provided") + "\n"
                "Functional Requirement: " + requirement + "\n"
                "Test Case Name: " + test_name + "\n\n"
                "Generate a complete Robot Framework test script targeting " + target_url_clean + "."
            )
        else:
            is_api = (
                "01_api" in target_suite.lower()
                or "api" in target_suite.lower()
                or any(kw in requirement.lower() for kw in ['api', 'endpoint', 'http', 'post', 'get', 'json', 'status code'])
            )
            system_prompt = SYSTEM_PROMPT_API if is_api else SYSTEM_PROMPT_UI
            user_prompt = f"Requirement: {requirement}\nTest Case Name: {test_name}\nTarget Suite: {target_suite}"

        api_key = os.getenv("GROQ_API_KEY", "").strip()

        # 2. Appel de l'API Groq Cloud
        if api_key:
            models = cls._get_available_models(api_key)
            last_error = None

            for model_id in models:
                try:
                    payload = json.dumps({
                        "model": model_id,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.2
                    }).encode("utf-8")

                    req = urllib.request.Request(
                        "https://api.groq.com/openai/v1/chat/completions",
                        data=payload,
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                            "User-Agent": "Mozilla/5.0"
                        },
                        method="POST"
                    )

                    with urllib.request.urlopen(req, timeout=30) as resp:
                        body = json.loads(resp.read().decode("utf-8"))
                        raw_code = body["choices"][0]["message"]["content"]

                        clean_code = cls._sanitize_and_fix_robot_code(
                            raw_code,
                            target_suite=target_suite,
                            requirement=requirement,
                            target_url=target_url_clean or None
                        )

                        return {
                            "status": "success",
                            "code": clean_code,
                            "provider": f"groq ({model_id})"
                        }

                except urllib.error.HTTPError as e:
                    err_body = e.read().decode("utf-8", errors="ignore")
                    last_error = f"HTTP {e.code}: {err_body}"
                    logger.warning(f"Groq model {model_id} failed: {last_error}")
                    continue
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"Groq model {model_id} error: {last_error}")
                    continue

            logger.error(f"All Groq models failed. Last error: {last_error}")

        # 3. Générateur de secours (Fallback)
        fallback_code = cls._generate_fallback(
            requirement=requirement,
            test_name=test_name,
            target_suite=target_suite,
            target_url=target_url_clean or None
        )
        return {
            "status": "success",
            "code": fallback_code,
            "provider": "fallback"
        }

    @classmethod
    def _generate_fallback(cls, requirement: str, test_name: str, target_suite: str, target_url: str = None) -> str:
        """Générateur déterministe de secours si l'API Groq est indisponible."""
        tc_title = test_name if test_name else "TC-AI Generated Test Case"
        req_lower = requirement.lower()

        # Cas 1 : URL externe
        if target_url and target_url.strip() and "localhost:4200" not in target_url:
            url_val = target_url.strip()
            return (
                "*** Settings ***\n"
                "Documentation    Automated test scenario generated for " + url_val + "\n"
                "Library          SeleniumLibrary\n\n"
                "*** Variables ***\n"
                "${TARGET_URL}    " + url_val + "\n\n"
                "*** Test Cases ***\n"
                + tc_title + "\n"
                "    [Documentation]    Test scenario for " + requirement + "\n"
                "    [Tags]             ai-generated    generic\n"
                "    Open Browser    ${TARGET_URL}    headlesschrome\n"
                "    Maximize Browser Window\n"
                "    Page Should Contain Element    xpath=//body\n"
                "    Close Browser\n"
            )

        # Cas 2 : Suite interne KPIT (Sara, Ahmed, Ali)
        if "sara" in req_lower:
            user_var, pass_var, name_var = "${SARA_LOGIN}", "${SARA_PASSWORD}", "${SARA_FIRST_NAME}"
        elif "ali" in req_lower:
            user_var, pass_var, name_var = "${ALI_LOGIN}", "${ALI_PASSWORD}", "${ALI_FIRST_NAME}"
        else:
            user_var, pass_var, name_var = "${AHMED_LOGIN}", "${AHMED_PASSWORD}", "${AHMED_FIRST_NAME}"

        is_error = any(w in req_lower for w in ["échec", "echec", "fail", "wrong", "mauvais", "erreur", "invalid", "invalide"])

        if is_error:
            wrong_pass = "WrongPass123"
            return f"""*** Test Cases ***
{tc_title}
    [Documentation]    Test généré automatiquement pour : {requirement}
    [Tags]             ai-generated    ui    security    error
    Perform Login    {user_var}    {wrong_pass}
    Verify Error Message Is Displayed    Invalid username or password
"""
        else:
            return f"""*** Test Cases ***
{tc_title}
    [Documentation]    Test généré automatiquement pour : {requirement}
    [Tags]             ai-generated    ui    smoke
    Perform Login    {user_var}    {pass_var}
    Verify Welcome Page Is Displayed
    Verify Welcome Message Contains    Welcome back, {name_var}
"""