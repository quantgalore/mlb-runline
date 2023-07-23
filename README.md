Original Source: [The Quant's Playbook](https://quantgalore.substack.com/)

This system stores the data in MySQL databases and the models in Colab notebooks. If you don’t have experience in setting these up, it is highly recommend visiting: 
[Machine Learning for Sports Betting: MLB Edition](https://www.quantgalore.com/courses/ml-sports-betting-mlb "Machine Learning for Sports Betting: MLB Edition"),
where we walk through the entire process with a similar workflow, going from data all the way to production.


The workflow for this algorithm is as follows:

1. Register for a [prop-odds](https://www.prop-odds.com/)  API key

2. Run the “mlb-runline-dataset-builder.py” file

	- This builds the original dataset and takes about 15-30 minutes

3. Run the “mlb-runline-daily.py” file

	- This is the dataset that will be used to get the predictions for the games of that day.

4. In Google Colab, run the “MLB_Runline_Training.ipynb” file

	- This file is responsible for comparing and training the dozens of available models. It isn't necessary to make any changes to the model, but you have the freedom to experiment.

	- Running the file will create a .pkl file containing the model of your choice, be sure to upload this to your drive.

5. In Google Colab, run the “MLB_Runline_Production.ipynb" file

	- This file will deploy the model you saved and generate predictions and theoretical odds.

6. In order to update new, future data points without having to re-build the entire dataset, run the “mlb-runline-dataset-production.py” in lieu of the “mlb-runline-dataset-builder.py”.

7. To start tracking predictions before going live, visit [the action network](https://www.actionnetwork.com/).

8. Finally, you're all set! 😄
