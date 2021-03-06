"""
Provides

Authors:
Hai Dong Luong (573780) <hai-ld>
Desmond Putra (555802) <dputra>
Andrew Vadnal (326558) <avadnal>
"""

from __future__ import division
from collections import defaultdict
from math import log10

"""
There are 3 classes in this file:
1. SRILangModel -> handles the Language Model. 
2. PhraseExtractor -> handles each sentence pair and word alignment
3. PhraseTabelExtractor -> handles the Translation model. It will utilize
   PhraseExtractor Class
"""

class SRILangModel:
    """
    This LM is generated by SRILM using an ARPA format. For the file format
    details can be seen on this website:
    http://www.speech.sri.com/projects/srilm/manpages/ngram-format.5.html

    Every n-gram in the LM has been converted into log base 10
    If a word is not exist in the LM then it will return a dummy value -99.
    """
    def __init__(self):
        self.lm_dict = {}
    
    def read_lm_file(self, file_name):
        """
        This function will read an output file from SRILM and 
        put it into dictionary. The value for the n-gram has already 
        been smoothed using long 10. So we don't need to do any comversion.

        For the time being we ignore the backoff-weights. We only focus on
        the value on the first column

        input: 
        file_name: SRILM output file name
        """
        f = open(file_name, 'r')
        sents = f.readlines()

        for line in sents:
            data = line.strip().split('\t')
            if len(data) > 1:
                self.lm_dict[data[1]] = float(data[0])

    def get_language_model_prob(self, ngram):
        """
        This function will return a probablity score given a n-gram words.
        input: 
        ngram : word/phrase

        output: probability score (using log10)
        """
        if ngram in self.lm_dict:
            return self.lm_dict[ngram]
        else:
            #if the word is not exist in LM, return the lowest log prob score
            return -99

class PhraseExtractor:
    """
    Extract phrase pairs from English and foreign sentences given their
    word alignment.

    Alignment is a list of tuples whose first items are indices of English
    words and second items are indices of foreign words.

    Modification:
    - I change the initialization for the f_start and f_end into len(f)-1 and -1
    """
    def __init__(self, e, f, alignment):
        self.e = e
        self.f = f
        self.alignment = alignment
        self.phrase_pairs = []

    def phrase_extract(self):
        """
        Extract and return phrase pairs.

        A phrase pair is a pair of tuples. First one is start and end index of
        English phrase, second one is start and end index of foreign phrase.
        """
        e, f, alignment = self.e, self.f, self.alignment

        # considers all possible English phrases
        for e_start in range(len(e)):
            for e_end in range(e_start, len(e)):
                f_start, f_end = len(f)-1, -1
                # find minimally aligned foreign phrase
                for e_i, f_i in alignment:
                    if e_start <= e_i <= e_end:
                        f_start = min(f_i, f_start)
                        f_end = max(f_i, f_end)
                
                self.phrase_pairs.extend(
                    self.extract(f_start, f_end, e_start, e_end)

                )
        return self.phrase_pairs

    def extract(self, f_start, f_end, e_start, e_end):
        """
        Extract and return phrase pairs with fixed English phrase.

        English phrase starts from e_start to e_end,
        foreign phrases include minimally aligned phrase f_start..f_end and
        phrases extended to neighboring unaligned words.

        Modification:
        - I put a handling if the f_end equals to -1
        - I put another extra rule in the consistency check
        
        input:
        f_start: start position of the foreign word 
        f_end: end position of the foreign word 
        e_start: start position of the english word 
        e_end: end position of the english word 

        output:
        list of phrase pair
        """
        if f_end == -1:
            return []

        # consistency check
        for e_i, f_i in self.alignment:
            #'e' position outside the phrase range
            if f_start <= f_i <= f_end and (e_i < e_start or e_i > e_end):
                return []
            #'f' position outside the phrase range
            if e_start <= e_i <= e_end and (f_i < f_start or f_i > f_end):
                return []

        phrase_pairs = []
        f_s = f_start
        while True:
            f_e = f_end
            while True:
                phrase_pair = ((e_start, e_end),(f_s, f_e))
                phrase_pairs.append(phrase_pair)
                f_e += 1
                if self.is_aligned(f_e):
                    break
            f_s -= 1
            if self.is_aligned(f_s):
                break
        return phrase_pairs

    def is_aligned(self, f):
        """Check if a foreign word is aligned"""
        if f < 0 or f >= len(self.f):
            return True
        for ae, af in self.alignment:
            if f == af:
                return True
        return False


class TranslationModel:
    """
    Extract phrase translation table of from word alignments.
    Alignments is a list of tuples whose first items are English sentences,
    second are foreign sentences and third are their word alignments.

    Modification:
    - Change the initialization value into english file, foreign file and 
    alignment file
    - I added read_file, format_alignment functions and get_phrase_prob func.
    """
    def __init__(self, file_e, file_f, file_alignment):
        self.file_e = file_e
        self.file_f = file_f
        self.file_alignment = file_alignment

        self.prob_fe = self.prob_ef = self.prob_oef = defaultdict(lambda: defaultdict(float))

    def read_file(self, file_name):
        """
        This function is used for reading the input file into an array
        and remove all the new line character
        """
        f = open(file_name, 'r')
        lines = [line.strip() for line in f]
        return lines

    def format_alignment(self,input_alignments):
        """
        The output format from giza++ for word alignment is (word_f-word_e) meanwhile
        in our project 1 code, we made a format (word_e, word_f). Therefore, in this
        function we change the separator from '-' to ',' and the direction as well
        to comply with our project 1 code
        """
        list_alignments = []

        for iteration in input_alignments:
            alignment_pairs = []
            word_pairs = iteration.split(" ")

            for word_pair in word_pairs:
                word = word_pair.split("-")
                alignment_pairs.append((int(word[1]),int(word[0])))
            
            list_alignments.append(alignment_pairs)
        return list_alignments

    def extract(self):
        """
        This function will extract all of the phrases by calling
        PhraseExtractor class and calculate the probability 
        for an english phrase given a foreign phrase (and vice versa).
        Each probability has been smoothed by utilizing log10.

        In addition, we tried to implement the lexical reordering model.
        We already made a function that will count the orientation (either
        monotone, swap or discontinue) from each phrase pair. However it 
        needs more detail information and time to connect it with 
        the translation model
        """
        #read all of the files
        list_sents_e = self.read_file(self.file_e)
        list_sents_f = self.read_file(self.file_f)
        list_raw_alignments = self.read_file(self.file_alignment)
        list_alignments = self.format_alignment(list_raw_alignments)
        
        """Extract phrase translation table."""
        count_oef = defaultdict(lambda: defaultdict(int))
        count_ef = defaultdict(lambda: defaultdict(int))
        count_e = defaultdict(int)
        count_f = defaultdict(int)
   
        for i in range(len(list_sents_e)):
            e = list_sents_e[i].split(" ")
            f = list_sents_f[i].split(" ")
            extractor = PhraseExtractor(e, f, list_alignments[i])

            phrase_pairs = extractor.phrase_extract()
            
            # count phrase occurrences
            for (e_start, e_end), (f_start, f_end) in phrase_pairs:
                e_phrase = ' '.join(e[e_start:e_end + 1])
                f_phrase = ' '.join(f[f_start:f_end + 1])
                count_ef[e_phrase][f_phrase] += 1
                count_e[e_phrase] += 1
                count_f[f_phrase] += 1

                #check the lexical reordering
                pair_ef = e_phrase + " " + f_phrase
                orientation = self.check_reordering(e_start, e_end, f_start, f_end, list_alignments[i])
                count_oef[orientation][pair_ef] +=1
        
        # Pr(f|e)
        prob_fe = defaultdict(lambda: defaultdict(float))
        # Pr(e|f)
        prob_ef = defaultdict(lambda: defaultdict(float))
        # Pr (o,e,f)
        prob_oef = defaultdict(lambda: defaultdict(float))
       
        for e_phrase in count_ef:
            for f_phrase in count_ef[e_phrase]:
                pair_ef = e_phrase + " " + f_phrase
                prob_fe[f_phrase][e_phrase] = log10(count_ef[e_phrase][f_phrase] / count_e[e_phrase])
                prob_ef[e_phrase][f_phrase] = log10(count_ef[e_phrase][f_phrase] / count_f[f_phrase])

                #add one smoothing to the lexical reordering
                prob_oef[orientation][pair_ef] = log10((count_oef[orientation][pair_ef]+1)/(count_ef[e_phrase][f_phrase]+1))
                
        self.prob_fe, self.prob_ef, self_prob_oef = prob_fe, prob_ef, prob_oef
        return prob_fe, prob_ef, prob_oef

    def check_reordering(self, e_start, e_end, f_start, f_end, list_alignment):
        """
        This function is used to check word alignment point whether it is
        monotone, swap or discontinue.

        Monotone: if word alignment point to the top left exists
        Swap: if word alignment point to the top right exists
        Discontinue: if word alignment point to the neither top left nor top right

        This function is not used in the current implementation due to the time constraint
        and need more details from the book about how to connect it with the translation model

        input:
        f_start: start position of the foreign word 
        f_end: end position of the foreign word 
        e_start: start position of the english word 
        e_end: end position of the english word 
        list_alignment: list of word alignment for that sentence

        output:
        orientation ("m", "s", "d")
        """     
        #default orientation
        orientation = "m"

        #check whether top left point to another word alignment or (-1,-1)
        if (((e_start-1),(f_start-1)) == (-1,-1)) or (((e_start-1),(f_start-1)) in list_alignment):
            orientation = "m"
        #check whether top right point to another word alignment
        elif ((e_start-1),(f_end+1)) in list_alignment:
            orientation = "s"
        #no adjacent
        else:
            orientation = "d"
        
        return orientation


    def get_translation_model_prob_f(self, word_f):
        """
        This function will read an english phrase and return a list of 
        foreign phrase and its probability

        input:
        word_f: foreign word/phrase

        output:
        list of translation from word_f and its probability score
        """

        my_dict = {}

        for word_e in self.prob_fe[word_f]:
            my_dict[word_e] = self.prob_fe[word_f][word_e]

        return my_dict

    def get_translation_model_prob_e(self, word_e):
        """
        This function will read a foreign phrase and return a list of 
        english phrase and its probability

        input:
        word_e: english word/phrase

        output:
        list of translation from word_e and its probability score
        """
        my_dict = {}

        for word_f in self.prob_ef[word_e]:
            my_dict[word_f] = self.prob_ef[word_e][word_f]

        return my_dict






