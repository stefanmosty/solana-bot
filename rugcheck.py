## This script checks if a token is a rug pull or not. It uses the RugCheck API to fetch the token data and performs the following checks:

from colorama import Fore, Style
import requests

RUG_CHECK_URL = "https://api.rugcheck.xyz/v1/tokens/{}/report"

# Establish the minimum amount of liquidity pool tokens that should be locked, 
# the minimum percentage of liquidity pool tokens that should be locked, 
# the maximum risk score, 
# and the maximum percentage of tokens that a single holder should own.
min_lp_locked_amount = 25000
min_lp_locked_pct = 75
max_risk_score = 501
max_holder_pct = 30

# Fetch the token data from the RugCheck API
def fetch_token_data(token_address):
 
    try:
        response = requests.get(RUG_CHECK_URL.format(token_address))
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching token data for {token_address}: {e}")
        return None

# Check if the top holders of the token own a percentage of tokens that is less than the maximum allowed percentage.
def check_top_holders(holders):
 
    if not holders:
        # print("No holders data found.")
        return False
    
    for holder in holders:
        if holder.get('pct', 0) > max_holder_pct:
            print(
            f"{Fore.YELLOW}Warning: One Holder owns {holder['pct']}%, exceeding the {max_holder_pct}% limit.{Style.RESET_ALL}"
            )
            return False
    # print("Top holders check passed.")
    return True

# Check if the liquidity pool tokens are burned by checking the amount of tokens locked, the percentage of tokens locked, and the locked status.
def check_lp_burned(markets):
     if not markets:
        # print("No markets data found.")
        return False

     raydium_market = next((market for market in markets if market.get("marketType") == "raydium"), None)
     if not raydium_market:
        return False
    
     lp = raydium_market.get('lp', {})  
     is_lp_locked = lp.get('lpLocked', 0)  
     lp_amount = lp.get('lpLockedUSD', 0)  
     lp_locked_pct = lp.get('lpLockedPct', 0)
    
    # Check the conditions for burning the LP tokens
     if is_lp_locked > 0 and lp_amount > min_lp_locked_amount and lp_locked_pct > min_lp_locked_pct:
        # print("Liquidity pool tokens are burned.")
        return True
    
    # print("Liquidity pool tokens are not burned.")
     return False

# Check if the risk score of the token is less than the maximum allowed risk score.
def check_max_risk_score(data):
 
    risk_score = data.get('score', 0)
    symbol = data.get('tokenMeta','N/A').get('symbol', 'N/A')
    token_address = data.get('mint', 'N/A')
    if risk_score > max_risk_score:
        print(f"{Fore.RED}Error: Risk score {risk_score} exceeds the maximum allowed. for {token_address} with {symbol} symbol {Style.RESET_ALL}")
        return False
    # print("Risk score check passed.")
    return True

# Check if the token is a rug pull by performing all the checks.
def check_token_is_not_rug(token_address):
 
    data = fetch_token_data(token_address)
    if not data:
        return False

    holders = data.get('Top Holders', [])
    markets = data.get('markets', [])
    # Perform all checks
    top_holders_valid = check_top_holders(holders)
    lp_burned = check_lp_burned(markets)
    is_risk_score_valid = check_max_risk_score(data)

    if  lp_burned and is_risk_score_valid:
        return True

    # print("Token is not compliant with checks.")
    return False

# Main function to check if a token is a rug pull or not.
if __name__ == "__main__":
    token_address = ""
    is_valid = check_token_is_not_rug(token_address)
    print(f"Token validity: {is_valid}")