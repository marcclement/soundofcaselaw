"Sound of Case-law can be used to transform judgments from the French Council of State and the Administrative Courts of Appeal into scores. The programme can process around 90,000 judgments (judgments since 2018 to work on the new wording introduced at that date). 

The programme automatically generates the musical score from the text of a judgment. For example, to listen to the Conseil d'État ruling of 12 July 2022, no. 447143, simply enter "447143" in the corresponding field. You can also make a random selection using the "Random generate" button. Use the 'Replay' button to replay the track. The 'Score' button displays the score. 

The programme uses the SCAMP Python library developed by Marc Evanstein. It can generate sounds and process several Midi instruments. The scores are created with the Lylipond program. Midi synthesis is done with Fluidsynth. The animations on the HTML page use the P5 Javascript library. 

To analyse the text of the judgements, we used a classification with a Bert model (FlauBert trained on the Jade database) as well as Stanza software for syntactic analysis.

Choosing an instrumental ensemble

Each score comprises a set of 6 musical lines.
For each judgement we determine the legal domain and for each legal domain we associate an instrumental ensemble with a basic "key" level (Midi value) for each instrument. 
For example, for the "Social" area, the following instrumental ensemble is used. 
{
"matiere" : "Social",
"instruments" : ["Xylophone 1","Xylophone 2", "Piano 1", "Piano 2", "Piano 3","Piano 4"],
"keys" : [84, 87 , 60, 84, 48, 30],
"levels" : [0.8, 0.8, 0.8, 0.8, 0.8, 0.8],
"tempo" : 60,
"scale" : "major"
}
In this case, Piano 1 will play on a scale of C major with a base starting on middle C, while Piano 3 will play on a base of C major but an octave lower. 

Microstructures

The judgement is separated into motivation part and operative part. Each paragraph is classified according to 12 labels corresponding to a stage in the legal reasoning. The classification method is based on a Bert-type algorithm adapted for French administrative court judgements. As a result, the judgment will be a succession of paragraphs : 
For instance for motivation part of case  447143 PROCEDURE TITRE REJETE TITRE REJETE TITRE TEXTE PRINCIPE ACCEPTE ACCEPTE FRAIS IRREPETIBLES then the paragraphs of the operative part PROCEDURE PROCEDURE FRAIS IRREPETIBLES FRAIS IRREPETIBLES PROCEDURE.

Each label is associated with a value :
{"PRINCIPE": 12, "PROCEDURE": 1, "REJETE":2, "ACCEPTE" : 3,
"TITRE" : 4, "TEXTE": 5, "AUTRE":6, "DEBUT MOTIFS":7,
"FRAIS IRREPETIBLES":8, "APPEL":9, "FIN REJET":10, "FIN ACCEPTE":11}

We are going to create a  musical "microstructure" from groups of four labels associated with values. For example, for the start of the judgement 447143, we have PROCEDURE TITRE REJETE TITRE, which gives the series of values 1 4 2 4 and therefore, if we take the value 48 as the basis, the following Midi values 49 53 50 48, which will be reflected in the following Midi notes because we are adjusting the values to the chosen scale (in this case major scale starting with C, C# does not belong to C Major so the closest note is chosen, which is D). 




For TITRE (headings) paragraphs, the microstructure is based on the words in the heading that are analysed.

For example, the first heading of judgment no. 447143 reads as follows « Sur les conclusions à fins de non-lieu à statuer présentées par l’association des habitants Plumereau-Halles-Résistance-Victoire de Tours » :


