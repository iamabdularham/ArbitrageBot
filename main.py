import requests
import json
import os
import time
import threading
import logging
from datetime import datetime
from dotenv import load_dotenv
from web3 import Web3
from flashbots import Flashbots

# Load environment variables from a .env file
load_dotenv()

# Initialize Web3 with Infura
infura_url = f"https://mainnet.infura.io/v3/{os.getenv('INFURA_PROJECT_ID')}"
web3 = Web3(Web3.HTTPProvider(infura_url))

# Initialize Flashbots
flashbots = Flashbots(web3)

# Configure logging
logging.basicConfig(
    filename="arbitrage_bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def fetch_live_prices():
    # Addresses for Uniswap and SushiSwap example pairs (e.g., WETH/USDC)
    uniswap_pair_address = Web3.to_checksum_address("0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc")  # Uniswap WETH/USDC
    sushiswap_pair_address = Web3.to_checksum_address("0x397FF1542f962076d0BFE58eA045FfA2d347ACa0")  # SushiSwap WETH/USDC

    # ABI for Uniswap/SushiSwap pair contract (simplified for getReserves)
    pair_abi = [
        {
            "constant": True,
            "inputs": [],
            "name": "getReserves",
            "outputs": [
                {"internalType": "uint112", "name": "_reserve0", "type": "uint112"},
                {"internalType": "uint112", "name": "_reserve1", "type": "uint112"},
                {"internalType": "uint32", "name": "_blockTimestampLast", "type": "uint32"}
            ],
            "payable": False,
            "stateMutability": "view",
            "type": "function"
        }
    ]

    try:
        # Fetch reserves from Uniswap
        uniswap_pair = web3.eth.contract(address=uniswap_pair_address, abi=pair_abi)
        uniswap_reserves = uniswap_pair.functions.getReserves().call()
        uniswap_price = (uniswap_reserves[0] / 10**6) / (uniswap_reserves[1] / 10**18)  # USDC/WETH

        # Fetch reserves from SushiSwap
        sushiswap_pair = web3.eth.contract(address=sushiswap_pair_address, abi=pair_abi)
        sushiswap_reserves = sushiswap_pair.functions.getReserves().call()
        sushiswap_price = (sushiswap_reserves[0] / 10**6) / (sushiswap_reserves[1] / 10**18)  # USDC/WETH

        # Debugging: Print raw reserve values
        print("Uniswap Reserves:", uniswap_reserves)
        print("SushiSwap Reserves:", sushiswap_reserves)

        print("Live Prices:")
        print(f"Uniswap WETH/USDC: {uniswap_price:.6f} USDC per WETH")
        print(f"SushiSwap WETH/USDC: {sushiswap_price:.6f} USDC per WETH")

        return uniswap_price, sushiswap_price
    except Exception as e:
        print(f"An error occurred while fetching prices: {e}")
        return None, None

def fetch_live_prices_with_timeout():
    try:
        # Use a thread to enforce a timeout for fetching live prices
        result = [None]

        def fetch():
            result[0] = fetch_live_prices()

        thread = threading.Thread(target=fetch)
        thread.start()
        thread.join(timeout=5)  # Timeout after 5 seconds

        if thread.is_alive():
            print("Fetching live prices timed out.")
            return None, None

        return result[0]
    except Exception as e:
        print(f"An error occurred while fetching live prices: {e}")
        return None, None

def fetch_buy_and_sell_prices():
    # Fetch both buying and selling prices from Uniswap and SushiSwap
    try:
        uniswap_pair_address = Web3.to_checksum_address("0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc")  # Uniswap WETH/USDC
        sushiswap_pair_address = Web3.to_checksum_address("0x397FF1542f962076d0BFE58eA045FfA2d347ACa0")  # SushiSwap WETH/USDC

        pair_abi = [
            {
                "constant": True,
                "inputs": [],
                "name": "getReserves",
                "outputs": [
                    {"internalType": "uint112", "name": "_reserve0", "type": "uint112"},
                    {"internalType": "uint112", "name": "_reserve1", "type": "uint112"},
                    {"internalType": "uint32", "name": "_blockTimestampLast", "type": "uint32"}
                ],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            }
        ]

        # Fetch reserves from Uniswap
        uniswap_pair = web3.eth.contract(address=uniswap_pair_address, abi=pair_abi)
        uniswap_reserves = uniswap_pair.functions.getReserves().call()
        uniswap_buy_price = (uniswap_reserves[1] / 10**6) / (uniswap_reserves[0] / 10**18)  # USDC/WETH
        uniswap_sell_price = (uniswap_reserves[0] / 10**6) / (uniswap_reserves[1] / 10**18)  # WETH/USDC

        # Fetch reserves from SushiSwap
        sushiswap_pair = web3.eth.contract(address=sushiswap_pair_address, abi=pair_abi)
        sushiswap_reserves = sushiswap_pair.functions.getReserves().call()
        sushiswap_buy_price = (sushiswap_reserves[1] / 10**6) / (sushiswap_reserves[0] / 10**18)  # USDC/WETH
        sushiswap_sell_price = (sushiswap_reserves[0] / 10**6) / (sushiswap_reserves[1] / 10**18)  # WETH/USDC

        # Temporary console logs for debugging
        print("Uniswap Reserves:", uniswap_reserves)
        print("Uniswap Buy Price:", uniswap_buy_price)
        print("Uniswap Sell Price:", uniswap_sell_price)
        print("SushiSwap Reserves:", sushiswap_reserves)
        print("SushiSwap Buy Price:", sushiswap_buy_price)
        print("SushiSwap Sell Price:", sushiswap_sell_price)

        return {
            "uniswap": {"buy": uniswap_buy_price, "sell": uniswap_sell_price},
            "sushiswap": {"buy": sushiswap_buy_price, "sell": sushiswap_sell_price}
        }
    except Exception as e:
        print(f"An error occurred while fetching buy and sell prices: {e}")
        return None

def calculate_gas_price():
    # Updated to use Infura API for gas prices
    infura_url = f"https://mainnet.infura.io/v3/{os.getenv('INFURA_PROJECT_ID')}"
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_gasPrice",
        "params": [],
        "id": 1
    }

    try:
        response = requests.post(infura_url, json=payload, auth=(os.getenv('INFURA_PROJECT_ID'), os.getenv('INFURA_SECRET_KEY')))
        if response.status_code == 200:
            data = response.json()
            gas_price_wei = int(data["result"], 16)  # Convert hex to integer
            gas_price_gwei = gas_price_wei / 1e9  # Convert Wei to Gwei
            print(f"Current Gas Price: {gas_price_gwei:.2f} Gwei")
        else:
            print(f"Error fetching gas prices: {response.status_code}")
    except Exception as e:
        print(f"An error occurred: {e}")

def fetch_dynamic_gas_price():
    # Fetch real-time gas price from Infura
    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_gasPrice",
            "params": [],
            "id": 1
        }
        response = requests.post(infura_url, json=payload)
        if response.status_code == 200:
            data = response.json()
            gas_price_wei = int(data["result"], 16)  # Convert hex to integer
            gas_price_gwei = gas_price_wei / 1e9  # Convert Wei to Gwei
            print(f"Dynamic Gas Price: {gas_price_gwei:.2f} Gwei")
            return gas_price_gwei
        else:
            print(f"Error fetching gas price: {response.status_code}")
            return None
    except Exception as e:
        print(f"An error occurred while fetching gas price: {e}")
        return None

def calculate_gas_cost(gas_price_gwei, gas_limit=21000):
    # Calculate gas cost in USDC
    eth_to_usdc_rate = 1800  # Example ETH to USDC conversion rate
    gas_cost_eth = (gas_price_gwei * 1e-9) * gas_limit
    gas_cost_usdc = gas_cost_eth * eth_to_usdc_rate
    print(f"Gas Cost: {gas_cost_usdc:.2f} USDC")
    return gas_cost_usdc

def calculate_slippage_impact(reserves, trade_amount, is_buy):
    # Simulate the trade to calculate slippage impact
    try:
        reserve_in, reserve_out = reserves
        if is_buy:
            # Buying: Calculate the amount of output tokens received for the input amount
            new_reserve_in = reserve_in + trade_amount
            new_reserve_out = reserve_out * reserve_in / new_reserve_in
            slippage_impact = reserve_out - new_reserve_out
        else:
            # Selling: Calculate the amount of input tokens required for the output amount
            new_reserve_out = reserve_out - trade_amount
            new_reserve_in = reserve_in * reserve_out / new_reserve_out
            slippage_impact = new_reserve_in - reserve_in

        return slippage_impact
    except Exception as e:
        print(f"An error occurred while calculating slippage impact: {e}")
        return None

def find_arbitrage_opportunities():
    uniswap_price, sushiswap_price = fetch_live_prices()
    if uniswap_price is None or sushiswap_price is None:
        print("Unable to fetch prices. Skipping arbitrage calculation.")
        return

    gas_price_gwei = fetch_dynamic_gas_price()
    if gas_price_gwei is None:
        print("Skipping iteration due to gas price fetch failure.")
        return

    gas_cost_usdc = calculate_gas_cost(gas_price_gwei, gas_limit=210000)  # Example gas limit for a trade

    # Slippage tolerance (e.g., 0.5% = 0.005)
    slippage_tolerance = 0.005

    # Adjust prices for slippage
    uniswap_price_with_slippage = uniswap_price * (1 + slippage_tolerance)
    sushiswap_price_with_slippage = sushiswap_price * (1 - slippage_tolerance)

    # Example trade amount in WETH (adjust as needed)
    trade_amount = 1  # 1 WETH

    # Calculate slippage impact for Uniswap and SushiSwap
    uniswap_slippage = calculate_slippage_impact((uniswap_reserves[0], uniswap_reserves[1]), trade_amount, is_buy=True)
    sushiswap_slippage = calculate_slippage_impact((sushiswap_reserves[0], sushiswap_reserves[1]), trade_amount, is_buy=True)

    print(f"Uniswap Slippage Impact: {uniswap_slippage:.6f}")
    print(f"SushiSwap Slippage Impact: {sushiswap_slippage:.6f}")

    # Adjust prices for slippage
    uniswap_price_with_slippage -= uniswap_slippage
    sushiswap_price_with_slippage -= sushiswap_slippage

    if uniswap_price_with_slippage < sushiswap_price_with_slippage:
        profit = sushiswap_price_with_slippage - uniswap_price_with_slippage - gas_cost_usdc
        if profit > 0:
            print(f"Arbitrage Opportunity: Buy on Uniswap at {uniswap_price:.6f} and sell on SushiSwap at {sushiswap_price:.6f}. Profit: {profit:.6f} USDC")
        else:
            print("No profitable arbitrage opportunity after accounting for gas and slippage.")
    elif sushiswap_price_with_slippage < uniswap_price_with_slippage:
        profit = uniswap_price_with_slippage - sushiswap_price_with_slippage - gas_cost_usdc
        if profit > 0:
            print(f"Arbitrage Opportunity: Buy on SushiSwap at {sushiswap_price:.6f} and sell on Uniswap at {uniswap_price:.6f}. Profit: {profit:.6f} USDC")
        else:
            print("No profitable arbitrage opportunity after accounting for gas and slippage.")
    else:
        print("No arbitrage opportunities found.")

def find_arbitrage_opportunities_with_depth():
    prices = fetch_buy_and_sell_prices()
    if not prices:
        print("Unable to fetch prices. Skipping arbitrage calculation.")
        return

    uniswap_buy = prices["uniswap"]["buy"]
    uniswap_sell = prices["uniswap"]["sell"]
    sushiswap_buy = prices["sushiswap"]["buy"]
    sushiswap_sell = prices["sushiswap"]["sell"]

    print("Prices:")
    print(f"Uniswap - Buy: {uniswap_buy:.6f}, Sell: {uniswap_sell:.6f}")
    print(f"SushiSwap - Buy: {sushiswap_buy:.6f}, Sell: {sushiswap_sell:.6f}")

    # Calculate arbitrage opportunities
    if uniswap_buy < sushiswap_sell:
        profit = sushiswap_sell - uniswap_buy
        print(f"Arbitrage Opportunity: Buy on Uniswap at {uniswap_buy:.6f} and sell on SushiSwap at {sushiswap_sell:.6f}. Profit: {profit:.6f} USDC")
    elif sushiswap_buy < uniswap_sell:
        profit = uniswap_sell - sushiswap_buy
        print(f"Arbitrage Opportunity: Buy on SushiSwap at {sushiswap_buy:.6f} and sell on Uniswap at {uniswap_sell:.6f}. Profit: {profit:.6f} USDC")
    else:
        print("No arbitrage opportunities found.")

def is_transaction_worth(profit, flashloan_amount):
    # Aave flashloan interest rate (0.09%)
    flashloan_interest_rate = 0.0009
    flashloan_interest = flashloan_amount * flashloan_interest_rate

    # Check if profit covers flashloan interest and is still positive
    return profit > flashloan_interest

def fetch_flashloan_fee():
    # Fetch flashloan fee dynamically (example for Aave)
    try:
        # Placeholder: Replace with actual API or contract call to fetch flashloan fee
        flashloan_fee_rate = 0.0009  # Aave's default flashloan fee rate (0.09%)
        print(f"Flashloan Fee Rate: {flashloan_fee_rate * 100:.2f}%")
        return flashloan_fee_rate
    except Exception as e:
        print(f"An error occurred while fetching flashloan fee: {e}")
        return None

def monitor_arbitrage_opportunities():
    print("Starting arbitrage monitoring...")
    try:
        while True:
            uniswap_price, sushiswap_price = fetch_live_prices_with_timeout()
            if uniswap_price is None or sushiswap_price is None:
                print("Unable to fetch prices. Skipping this iteration.")
                time.sleep(2)  # Reduced wait time before retrying
                continue

            gas_price_gwei = fetch_dynamic_gas_price()
            if gas_price_gwei is None:
                print("Skipping iteration due to gas price fetch failure.")
                return

            gas_cost_usdc = calculate_gas_cost(gas_price_gwei, gas_limit=210000)  # Example gas limit for a trade

            # Slippage tolerance (e.g., 0.5% = 0.005)
            slippage_tolerance = 0.005

            # Adjust prices for slippage
            uniswap_price_with_slippage = uniswap_price * (1 + slippage_tolerance)
            sushiswap_price_with_slippage = sushiswap_price * (1 - slippage_tolerance)

            flashloan_amount = 1000  # Example flashloan amount in USDC

            flashloan_fee_rate = fetch_flashloan_fee()
            if flashloan_fee_rate is None:
                print("Skipping iteration due to flashloan fee fetch failure.")
                return

            flashloan_fee = flashloan_amount * flashloan_fee_rate
            print(f"Flashloan Fee: {flashloan_fee:.2f} USDC")

            profit_threshold = 10  # Minimum profit threshold in USDC

            net_profit = simulate_transaction(
                buy_price=uniswap_price_with_slippage,
                sell_price=sushiswap_price_with_slippage,
                trade_amount=1,  # Example trade amount in WETH
                gas_cost=gas_cost_usdc,
                flashloan_fee=flashloan_fee
            )

            if net_profit and net_profit > profit_threshold:
                logging.info(f"Profitable opportunity detected: {net_profit:.2f} USDC")
                send_notification(f"Profitable opportunity: {net_profit:.2f} USDC")
                execute_transaction()
            else:
                logging.info("No profitable opportunities above the threshold.")

            # Store historical data
            store_historical_data({
                "uniswap_price": uniswap_price,
                "sushiswap_price": sushiswap_price,
                "net_profit": net_profit
            })

            if uniswap_price_with_slippage < sushiswap_price_with_slippage:
                profit = sushiswap_price_with_slippage - uniswap_price_with_slippage - gas_cost_usdc - flashloan_fee
                if is_transaction_worth(profit, flashloan_amount):
                    print(f"Arbitrage Opportunity: Buy on Uniswap at {uniswap_price:.6f} and sell on SushiSwap at {sushiswap_price:.6f}. Profit: {profit:.6f} USDC")
                else:
                    print("Opportunity not worth executing after accounting for flashloan interest.")
            elif sushiswap_price_with_slippage < uniswap_price_with_slippage:
                profit = uniswap_price_with_slippage - sushiswap_price_with_slippage - gas_cost_usdc - flashloan_fee
                if is_transaction_worth(profit, flashloan_amount):
                    print(f"Arbitrage Opportunity: Buy on SushiSwap at {sushiswap_price:.6f} and sell on Uniswap at {uniswap_price:.6f}. Profit: {profit:.6f} USDC")
                else:
                    print("Opportunity not worth executing after accounting for flashloan interest.")
            else:
                print("No arbitrage opportunities found.")

            time.sleep(2)  # Reduced wait time between iterations
    except KeyboardInterrupt:
        print("Arbitrage monitoring stopped.")

def submit_transaction_via_flashbots(transaction):
    try:
        # Submit the transaction bundle via Flashbots
        bundle = [{"signed_transaction": transaction}]
        response = flashbots.send_bundle(bundle, target_block_number=web3.eth.block_number + 1)
        if response["success"]:
            print("Transaction successfully submitted via Flashbots.")
        else:
            print("Flashbots submission failed.")
    except Exception as e:
        print(f"An error occurred while submitting via Flashbots: {e}")

def monitor_mempool():
    print("Monitoring mempool for profitable transactions...")
    try:
        while True:
            # Example logic to monitor mempool (simplified)
            pending_transactions = web3.eth.get_block("pending")["transactions"]
            for tx in pending_transactions:
                # Analyze transaction for profitability (placeholder logic)
                if is_profitable_transaction(tx):
                    print(f"Profitable transaction detected: {tx}")
                    # Submit a frontrunning transaction via Flashbots
                    submit_transaction_via_flashbots(tx)
            time.sleep(1)  # Poll the mempool every second
    except KeyboardInterrupt:
        print("Mempool monitoring stopped.")

def is_profitable_transaction(transaction):
    # Analyze the transaction to determine if it is profitable
    try:
        # Extract relevant details from the transaction
        gas_price = transaction.get('gasPrice', 0)
        value = transaction.get('value', 0)
        input_data = transaction.get('input', '')

        # Placeholder: Check if the transaction involves a known DEX pair (e.g., WETH/USDC)
        if "WETH" in input_data and "USDC" in input_data:
            # Estimate the cost of the transaction in USDC
            gas_cost_usdc = (gas_price / 1e9) * 0.0001  # Example conversion rate

            # Placeholder: Simulate the transaction to estimate profit
            estimated_profit = value - gas_cost_usdc

            # Return True if the profit is positive
            return estimated_profit > 0

        return False
    except Exception as e:
        print(f"An error occurred while analyzing the transaction: {e}")
        return False

def simulate_transaction(buy_price, sell_price, trade_amount, gas_cost, flashloan_fee):
    # Simulate the transaction to calculate net profit
    try:
        total_cost = buy_price * trade_amount + gas_cost + flashloan_fee
        total_revenue = sell_price * trade_amount
        net_profit = total_revenue - total_cost
        return net_profit
    except Exception as e:
        logging.error(f"Error in transaction simulation: {e}")
        return None

def add_dex_support():
    # Placeholder for adding support for additional DEXs like PancakeSwap or Curve
    logging.info("Adding support for additional DEXs is a future enhancement.")

def store_historical_data(data):
    # Store historical price and transaction data for analysis
    try:
        with open("historical_data.csv", "a") as file:
            file.write(f"{datetime.now()},{data}\n")
    except Exception as e:
        logging.error(f"Error storing historical data: {e}")

def send_notification(message):
    # Placeholder for sending real-time notifications (e.g., via email or Telegram)
    logging.info(f"Notification sent: {message}")

def execute_transaction():
    # Placeholder for automating transaction execution
    logging.info("Transaction execution is a future enhancement.")

def main():
    print("Welcome to the Arbitrage Bot!")
    monitor_arbitrage_opportunities()

if __name__ == "__main__":
    main()