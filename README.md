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


![Alt text](/images/howitworks_html_5c26094.gif?raw=true "image")

For TITRE (headings) paragraphs, the microstructure is based on the words in the heading that are analysed.

For example, the first heading of judgment no. 447143 reads as follows « Sur les conclusions à fins de non-lieu à statuer présentées par l’association des habitants Plumereau-Halles-Résistance-Victoire de Tours »  and is transformed to the following microstructure by associating each word with a pitch related to the first letter of the word (a is 1, b is 2 etc) and the duration is based on the lenght of the word. A random reductions of note is performed to avoid too many notes.  


![Alt text](/images/howitworks_html_7cf9e655.gif?raw=true "image")

Transformations of microstructures

Microstructures are associated with possible transformations operating on each parameter of a note (pitch, lenght, volume).

volume_wave
Create a  crescendo-decrescendo effect on the microstructure with maximum in the middle note

reverse
Reverse notes in microstructure 

isolate
Only n note in microstructure is kept.

isolate_long
The n note in microstructure is kept with duration until the end of microstructure with silence before note.

transpose
All notes in microstructure are played with pitch + n value.

superpose
All notes in microstructure are played in a chord which has the duration of the microstructure.

drop
Every n notes in microstructure is replaced by silence.

slide
The note n in microstructure is modified by modifying its duration with random

arpegiaze
Fill the duration between 2 consecutives notes with notes in interval. For instance if intervals given is [0, 4, 7]  a C (60 midi) is transformed in a pattern with C  E  G (60+0, 60+4, 60+7)

pattern
Keep n notes in microstructures and fill the duration between notes with a pattern consisting in a array of pitches.

converge
Pitch of each note is reduced or augmented  by n in reference to a focus note. For instance if first note is 60 and focus note is 78 with step 2 pitch is ajusted to 62.

patterns

For each paragraph, the microstructure is associated with each instrument to create a vertical musical structure called a pattern. Here are the first 2 bars of case 447143 with the microstructure developed for instrument 2 (Xylophone 2) and instrument 5 (Piano 3). Instrument 4 (Piano 2) uses the "isolate_long" microstructure transformation, keeping only note n of a microstructure starting with a silence if it's not the first note and extending to the end of the microstructure (over 8 beats). 


Score

The complete partition is the result of a succession of patterns (one pattern per paragraph) with transformations applied to the microstructures according to the type of paragraph encountered. 

Instruments 4, 5 and 6 play a base that remains the same whatever the paragraph: instrument 6 plays the microstructure without modification, instrument 5 plays the same microstructure with a "slide" transformation and instrument 6 plays the microstructure with the "isolate_long" transformation.

Instrument 1 plays the microstructure with a different transformation depending on the paragraph label, for example if the label is "TEXTE" then the transformation applied is "reverse", if the label is « PRINCIPE » then the transformation is « arpegiaze » with [1, 3] : note is increased by one semitone and the duration is split to create a new note 3 semitones higher. 
Instrument 2 plays « PROCEDURE » paragraphs. 
Instrument 3 plays only « TITRE » microstructure. 

![Alt text](/images/images/howitworks_html_702ab1d3.gif?raw=true "image")




