# TODO
# Need to incorporate player offensive rating and team defensive rating somehow. Potential uses could be adding/subtracting to the montecarlo mean, or even using it to scale it.
# Include better viewing capability on the lines, and potential sorting options
# Refactor?

import pandas as pd
import urllib
import bs4 as bs
import numpy as np

team_conferences = {
    'Atlanta Hawks': 'Eastern',
    'Boston Celtics': 'Eastern',
    'Brooklyn Nets': 'Eastern',
    'Charlotte Hornets': 'Eastern',
    'Chicago Bulls': 'Eastern',
    'Cleveland Cavaliers': 'Eastern',
    'Detroit Pistons': 'Eastern',
    'Indiana Pacers': 'Eastern',
    'Miami Heat': 'Eastern',
    'Milwaukee Bucks': 'Eastern',
    'New York Knicks': 'Eastern',
    'Orlando Magic': 'Eastern',
    'Philadelphia 76ers': 'Eastern',
    'Toronto Raptors': 'Eastern',
    'Washington Wizards': 'Eastern',
    'Dallas Mavericks': 'Western',
    'Denver Nuggets': 'Western',
    'Golden State Warriors': 'Western',
    'Houston Rockets': 'Western',
    'Los Angeles Clippers': 'Western',
    'Los Angeles Lakers': 'Western',
    'Memphis Grizzlies': 'Western',
    'Minnesota Timberwolves': 'Western',
    'New Orleans Pelicans': 'Western',
    'Oklahoma City Thunder': 'Western',
    'Phoenix Suns': 'Western',
    'Portland Trail Blazers': 'Western',
    'Sacramento Kings': 'Western',
    'San Antonio Spurs': 'Western',
    'Utah Jazz': 'Western'
}


def predict_player_line(player_url, opponent, vegas_information):


    # Retrieve data

    source = urllib.request.urlopen(player_url).read()
    soup = bs.BeautifulSoup(source,'lxml')
    table = str(soup.find_all('table')[0])
    data = pd.read_html(table)[0]


    # Preprocessing
        
    data = data.drop(index=data.index[-2:]) # Remove last two rows as they're totals
    data = data[data["Min"] != "DNP"] # remove any games where he did not play

    # Turn minutes into a number of minutes
    def time_to_minutes(time_str):
        minutes, seconds = map(int, time_str.split(':'))
        return minutes + seconds / 60
    data["Min"] = data["Min"].apply(time_to_minutes)

    for float_col in ["Min", "PTS", "REB", "AST"]: # ensure all numeric columns are casted to double
        data[float_col] = data[float_col].astype("float64")

    # Add team's conference to data
    data["Conference"] = data["Opp"].map(team_conferences)


    for prop in vegas_information:
        
        # Map prop to respective column name
        prop_to_column = {"Points" : "PTS", "Rebounds" : "REB", "Assists" : "AST"}
        column = prop_to_column[prop]

        # Calculate Projection
        projected_average = calculate_projected_average(data, column, opponent)


        # Run Montecarlo 
        std = np.array(data[column]).std()  # calculate standard deviation from point history
        n = 100000 # number of iterations

        samples = np.random.normal(projected_average, std, n)

        # Counting how many samples are above the check_value
        count_above = np.sum(samples > vegas_information[prop]["Line"])

        vegas_information[prop]["Over Probability"] = count_above/n
        vegas_information[prop]["Under Probability"] = (n - count_above)/n


def calculate_projected_average(data, column, opponent):

    averages = [] # Create list of averages to find mean over

    # Find way to determine if home or away game?
    
    averages.append(((data[column]/data["Min"]) * data["Min"]).mean()) # get the average of average points per minute multiplied by average minutes
    averages.append(data[:-1][column].iloc[0]) # previous game
    averages.append(data[-5:][column].mean()) # last 5 games
    averages.append(data[-10:][column].mean()) # last 10 games 
    if not pd.isna(data[data["Opp"] == opponent][column].mean()): # games where they played the opponent, check to make sure one exists
        averages.append(data[data["Opp"] == opponent][column].mean())
    if not pd.isna(data[data["Conference"] == team_conferences[opponent]][column].mean()): # games where they played the conference, check to make sure one exists
        averages.append(data[data["Conference"] == team_conferences[opponent]][column].mean())

    return np.array(averages).mean() # get average of accumulated values


def vegas_to_probability(vegas_odds):
        
        if vegas_odds > 0:
            decimal_odds = (vegas_odds / 100) + 1
        else:
            decimal_odds = (100 / abs(vegas_odds)) + 1

        return (1 / decimal_odds)

def find_bets(data, show_all=False):

    print("Betting Lines")
    print("-------------------------")

    for prop, details in data.items():
        
        line = details['Line']
        
        vegas_over_odds = details['Over']
        vegas_under_odds = details['Under']

        # Convert Vegas odds to probabilities
        prob_over_vegas = vegas_to_probability(vegas_over_odds)
        prob_under_vegas = vegas_to_probability(vegas_under_odds)

        # Compare with calculated probabilities
        if show_all:
            print(f"{prop} Over: Line {line}, Calculated Probability: {details['Over Probability']:.2%}, Vegas Probability: {prob_over_vegas:.2%}, Calculated difference of {details['Over Probability']-prob_over_vegas:.2%}")
            print(f"{prop} Under: Line {line}, Calculated Probability: {details['Under Probability']:.2%}, Vegas Probability: {prob_under_vegas:.2%}, Calculated difference of {details['Under Probability']-prob_under_vegas:.2%}")

        else:
            if details['Over Probability'] > prob_over_vegas:
                print(f"{prop} Over: Line {line}, Calculated Probability: {details['Over Probability']:.2%}, Vegas Probability: {prob_over_vegas:.2%}")
            if details['Under Probability'] > prob_under_vegas:
                print(f"{prop} Under: Line {line}, Calculated Probability: {details['Under Probability']:.2%}, Vegas Probability: {prob_under_vegas:.2%}")


if __name__ == "__main__":

    player_url = "https://www.teamrankings.com/nba/player/victor-wembanyama/game-log"
    opponent = "Utah Jazz"

    show_all = True # Show whether to print all odds or just the favourable ones
    
    vegas_info = {
        "Points": {"Line" : 18.5, "Under" : -113, "Over" : -113},
        "Rebounds": {"Line" : 10.5, "Under" : +108, "Over" : -138},
        "Assists": {"Line" : 2.5, "Under" : +132, "Over" : -170}
    }
    
    predict_player_line(player_url, opponent, vegas_info)

    find_bets(vegas_info, show_all)
    
