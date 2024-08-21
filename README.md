# trading-bot

These are simulator and production cryptocurrencies trading bots built with python. These bots work with Futures Binance API.
The simulator downloads historical data from API, stores on a folder called data and then makes the simulations.

## tester bot of BTCUSDT

In order to run the tester simulator, you should:

1. Set a virtual environment.

2. Install the dependencies located in tester/requirements.txt.

3. Run test_tester.ipynb notebook (if you get an error of folder named data missing, just create one: tester/data).

### How to make my strategy?

1. Make a child class from tester.py inside a new file new_file.py

2. Implement the methods prepare_strategy and run_strategy from the parent class with your strategy, you can see examples in tester_<placeholder>.py 

3. Run test_tester.ipynb notebook importing your class as first line.

### What if I want to test other futures pairs?

Currently simulation of other pairs is not available.

## production bot of BTCUSDT

1. Set a virtual environment.

2. Install the dependencies located in production/requirements.txt.

3. Once you have your strategy, copy it to strategy.py file in a new file and overwrite the same methods prepare_strategy and run_strategy from simulation. Notice that instead of a variable storing your strategy (in my case I called the variable "strategy"), now you have to set it as an attribute (in my case "self.strategy") in order to be persistent for class during streaming.

4. Make a statuscake ping URL in order to monitor your online status.

5. Run the bot using run_bot.py (please adjust the init params to your needs).

6. (Optional) If you want to run the bot in EC2 instance, see file ec2_instructions/howtouse.md
