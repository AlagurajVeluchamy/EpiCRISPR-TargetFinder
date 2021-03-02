import os
import re
import string
from Bio import SeqIO
import subprocess
from subprocess import call, Popen, PIPE
import glob
from Bio.Seq import Seq
##from Bio.Alphabet import generic_dna
import numpy
import pandas as pd
import sys
import csv
csv.field_size_limit(sys.maxsize)

##import psutil


def checkpam(argu, chr,start,secondaryhitpattern,strand, getgenome, querysequence, secondaryhitmismatch):
    length = score = ggfound = 0
    forwardseq = revcomplementseq = complementseq = "NONE"
    for record in getgenome:
        recordid = str(record.id)
        #if (strand == 0 or strand <= 256) and recordid == chr:
        if (strand == "+" ) and recordid == chr:
            forwardseq = str(record.seq)[start-1:start+22]
            if forwardseq.endswith(argu.pamsequence):
                ggfound = ggfound + 1
            elif argu.pamsequence in forwardseq[-4:]:
                ggfound = ggfound + 1
        elif (strand == "-") and recordid == chr:
            complementseq = str(record.seq)[start-1:start + 22]
            newseq = Seq(complementseq)
            revcomplementseq = str(newseq.reverse_complement())
            if revcomplementseq.endswith(argu.pamsequence):
                ggfound = ggfound + 1
            elif argu.pamsequence in revcomplementseq[-4:]:
                ggfound = ggfound + 1
    if ggfound > 0:
        #print ("inside checkpam.. before getscore")
        (length, score) = getscore(secondaryhitpattern, secondaryhitmismatch)
    return(length, score, ggfound,forwardseq,revcomplementseq)

def getscore(pattern,secondaryhitmismatch):
    matchpat = re.findall("(\d+)M", pattern)
    #mismatchpat = re.findall("(\d+)X", pattern)
    insertionpat = re.findall("(\d+)I", pattern)
    deletionpat = re.findall("(\d+)D", pattern)
    substitutionpat = re.findall("(\d+)D", pattern)
    #print("inside checkpam.. inside getscore")
    if len(matchpat) > 0:
        summatchpat = sum(map(int, matchpat))
    else:
        summatchpat = 0
    if len(substitutionpat) > 0:
        substitutionpat = sum(map(int, substitutionpat))
    else:
        substitutionpat = 0
    if len(insertionpat) > 0:
        suminsertionpat = sum(map(int, insertionpat))
    else:
        suminsertionpat = 0
    length = summatchpat + substitutionpat + suminsertionpat
    score = round(float(summatchpat - int(secondaryhitmismatch) - suminsertionpat)/float(length), 3)
    return(length, score)


def calculatewrite(argu, fileoutmap, gc_content, counthits, countoffhits, inwindscore, outwindscore, queryname, querychr, arbitraryid, querystart, offtargetlist, secondaryhitschr, bestwindow, newlist, querysequence, getstddev):
    import string
    suminwindscore = sum(map(float, inwindscore))
    sumoutwindscore = sum(map(float, outwindscore))
    finalscore = ((float(counthits) * (suminwindscore/float(counthits)))/float(counthits+countoffhits)) - ((float(countoffhits) * (sumoutwindscore/float(countoffhits)))/float(counthits+countoffhits))
    ### Below sequence translate take more time ###
    if counthits > argu.minhits:
        if "candidaternars" in queryname:
            ## For python 3.0 it changed to str.maketrans
            #complements = string.maketrans('ATGC', 'TACG')
            #complements = str.maketrans('ATGC', 'TACG')
            #print (querysequence)
            #querysequence = querysequence.translate(complements)[::-1]
            #print (querysequence)
            ############ Above sequence translate take more time ###
            fileoutmap.write(str(queryname) + "_" + str(querychr) + "_" + str(arbitraryid) + "_" + str(querystart) + "\t" + str(querysequence) + "\t" + str(gc_content)+ "\t" + str(finalscore) + "\t" + str(getstddev) + "\t" + str(suminwindscore) + "\t" + str(sumoutwindscore) +  "\t" + str(counthits) + "\t" + str(len(offtargetlist)) + "\t" + str(querychr) + ":" + str(min(bestwindow)) + "-" + str(max(bestwindow)) + "\t" + str(newlist) + "\n")
        elif "candidaternafs" in queryname:
            fileoutmap.write(str(queryname) + "_" + str(querychr) + "_" + str(arbitraryid) + "_" + str(querystart) + "\t" + str(querysequence) + "\t" + str(gc_content) + "\t" + str(finalscore) + "\t" + str(getstddev) + "\t" + str(suminwindscore) + "\t" + str(sumoutwindscore) + "\t" + str(counthits) + "\t" + str(len(offtargetlist)) + "\t" + str(querychr) + ":" + str(min(bestwindow)) + "-" + str(max(bestwindow)) + "\t" + str(newlist) + "\n")
    elif counthits < 1:
        print ("Pattern Match error")

def calculatestdev(bestwindow):
    if len(bestwindow) > 4:
        getstddev = numpy.std(bestwindow, axis=0)
    else:
        getstddev = "NULL"
    return getstddev

def overlapeachchromosome(argu, splitinputfile):
    print ("Processing:",splitinputfile)
    getgenome = list(SeqIO.parse(argu.genomesplitfasta, "fasta"))
    splitinputfilefiltered = splitinputfile
    splitinputfileresult = splitinputfile + "_scores.txt"
    splitinputfileline1error = splitinputfile + "_line1_error.txt"
    splitinputfileline2error = splitinputfile + "_line2_error.txt"
    fileinmap = open(splitinputfilefiltered, 'r')
    fileoutmap = open(splitinputfileresult, 'w')
    splitinputfileggerror = splitinputfile + "_GG_error.txt"
    fileoutline1error = open(splitinputfileline1error, 'w')
    fileoutline2error = open(splitinputfileline2error, 'w')
    fileoutggerror = open(splitinputfileggerror, 'w')
    fileoutstd = open(os.path.join(argu.workingdirectory,"EpiCrispr_std.xls"), 'a')
    # PROCESS = psutil.Process(os.getpid())
    # mem = PROCESS.memory_info().rss
    # print(f"Currently used memory={mem} KB")
    # MAX_MEMORY = max(mem, MAX_MEMORY)
    # print(f"Max Memory while threads running={MAX_MEMORY} KB")
    # time.sleep(0.0000001)
    for line in fileinmap:
        #line1 = re.search("(\w*)_(\w*)_(\w*)_(\d*)\t(\w*)\t(\w*)\t(\w*)\t(\w.*)\t(\w*)\t(.*?)\t(\w.*)\t(\w.*)\t(\w*)\t(.*?).*XA:Z:(\w*.*)", str(line))
        #line1 = re.search("(\w*)_(.*?)_(\w*)_(\d*)\t(\w*)\t(\w*)\t(\w*)\t(\w*)\tXA:Z:(.*?)\t(\d*.*)", str(line))
        line1 = re.search("(\w*)_(.*?)_(\w*)_(\d*)\t(.*?)\t(.*?)\t(\w*)\t(.*?)\t(.*?)\tXA:Z:(.*?)\t(.*?)", str(line))
        #print (line1)
        if line1:
            newlist = []
            offtargetlist = []
            #(queryname, querychr, arbitraryid, querystart, firsthitchr, firsthitstart, querysequence) = line1.group(1,2, 3, 4, 6, 7, 13)
            (queryname, querychr, arbitraryid, querystart, firsthitstrand, firsthitchr, querysequence, cigarstring) = line1.group(1, 2, 3, 4, 5, 6, 7, 10)
            if not querysequence.endswith(argu.pamsequence):
                queryreversed = Seq(querysequence)
                querysequence = str(queryreversed.reverse_complement())
            #print (cigarstring)
            gc_content = float((querysequence.count('G') + querysequence.count('C'))) / len(querysequence) * 100
            line2 = re.findall("(.*?),([-+])(\d.*?),(\w*.*?|\d*.*?),(\d.*?)\;", str(cigarstring))
            counthits = countoffhits = 1
            bestwindow = []
            inwindscores = []
            outwindscores = []
            #print (len(line2))
            if len(line2) >= int(argu.minhits):
                for eachtuple in line2:
                    secondaryhitschr = str(eachtuple[0])
                    secondaryhitsstrand = str(eachtuple[1])
                    secondaryhitsstart = int(eachtuple[2])
                    secondaryhitpattern = eachtuple[3]
                    secondaryhitmismatch = eachtuple[4]

                    (length, score, ggfound,forwardseq,revcomplementseq) = checkpam(argu, secondaryhitschr, secondaryhitsstart, secondaryhitpattern, secondaryhitsstrand, getgenome, querysequence,secondaryhitmismatch)
                    if ggfound > 0:
                        if querychr == secondaryhitschr and ((int(querystart) - argu.window) <= int(secondaryhitsstart) <= (int(querystart) + argu.window)):
                            inwindscores.append(score)
                            bestwindow.append(secondaryhitsstart)
                            counthits = counthits + 1
                            newlist.append(str(eachtuple))
                        else:
                            offtargetlist.append(str(eachtuple))
                            outwindscores.append(score)
                            countoffhits = countoffhits + 1
                    else:
                        fileoutggerror.write("PAM pattern not found at the 3'-end"+"\t"+str(forwardseq)+"\t"+str(revcomplementseq)+"\t"+str(secondaryhitschr)+"\t"+str(secondaryhitsstart)+"\t"+ str(querysequence)+"\n")
                getstddev = calculatestdev(bestwindow)
                fileoutstd.write(str(bestwindow)+ "\n")
                calculatewrite(argu, fileoutmap, gc_content, counthits, countoffhits, inwindscores, outwindscores, queryname, querychr, arbitraryid, querystart, offtargetlist, secondaryhitschr, bestwindow, newlist, querysequence, getstddev)
            elif len(line2) < 1:
                #print (len(line2), argu.minhits)
                fileoutline2error.write(str(len(line2)) + "\t" + str(argu.minhits) + "\t" + str(line1.group(6)))
                #print ("Filtered file from SAM is not valid", line)
        else:
            #print ("line1 error")
            fileoutline1error.write(str(line) + "\t" + str(argu.minhits)+str("\n"))
def getallresults(argu):
    print ("Pooling the results...")
    if os.path.exists(os.path.join(argu.workingdirectory,"EpiCRISPR_results.xls")):
        os.remove(os.path.join(argu.workingdirectory,"EpiCRISPR_results.xls"))
        print("Deleting the file from previous run..")
    else:
        print("Create a new result file EpiCRISPR_results.xls")
    fileoutmapfin = open(os.path.join(argu.workingdirectory,"EpiCRISPR_results.xls"), 'a')
    fileoutmapfin.write("Queryname\tQuery Sequence\tGC%\tFinalscore\tDispersion/Spread\tsuminwindscore\tsumoutwindscore\tNumber of hits in Best window\tNumber of hits outside Best window\tBest window\tHits within Best window"+"\n")
    fileoutmapfin.flush()
    pidcat = subprocess.Popen(["cat"] + glob.glob(str(os.path.join(argu.workingdirectory, "Candidate_crisprna.split")) + "*" + "_scores.txt"), stdout=subprocess.PIPE)
    pidsort = subprocess.Popen(["sort -k4 -n -r"], stdin=pidcat.stdout, stdout=fileoutmapfin, shell=True)



def overlapeachchromosomemorethanonewindow(argu, splitinputfile):
    print ("Processing:",splitinputfile)
    getgenome = list(SeqIO.parse(argu.genomesplitfasta, "fasta"))
    splitinputfilefiltered = splitinputfile
    splitinputfileresult = splitinputfile + "_scores.txt"
    splitinputfileline1error = splitinputfile + "_line1_error.txt"
    splitinputfileline2error = splitinputfile + "_line2_error.txt"
    fileinmap = open(splitinputfilefiltered, 'r')
    fileoutmap = open(splitinputfileresult, 'w')
    splitinputfileggerror = splitinputfile + "_GG_error.txt"
    fileoutline1error = open(splitinputfileline1error, 'w')
    fileoutline2error = open(splitinputfileline2error, 'w')
    fileoutggerror = open(splitinputfileggerror, 'w')
    fileoutstd = open(os.path.join(argu.workingdirectory,"Crispr_broad_multihits.xls"), 'a')
    # PROCESS = psutil.Process(os.getpid())
    # mem = PROCESS.memory_info().rss
    # print(f"Currently used memory={mem} KB")
    # MAX_MEMORY = max(mem, MAX_MEMORY)
    # print(f"Max Memory while threads running={MAX_MEMORY} KB")
    # time.sleep(0.0000001)
    counttest = 0
    for line in fileinmap:
        counttest = counttest + 1
        #if counttest > 1:
        #    exit()
        #line1 = re.search("(\w*)_(\w*)_(\w*)_(\d*)\t(\w*)\t(\w*)\t(\w*)\t(\w.*)\t(\w*)\t(.*?)\t(\w.*)\t(\w.*)\t(\w*)\t(.*?).*XA:Z:(\w*.*)", str(line))
        #line1 = re.search("(\w*)_(.*?)_(\w*)_(\d*)\t(\w*)\t(\w*)\t(\w*)\t(\w*)\tXA:Z:(.*?)\t(\d*.*)", str(line))
        line1 = re.search("(\w*)_(.*?)_(\w*)_(\d*)\t(.*?)\t(.*?)\t(\w*)\t(.*?)\t(.*?)\tXA:Z:(.*?)\t(.*?)", str(line))
        if line1:
            newlist = []
            offtargetlist = []
            #(queryname, querychr, arbitraryid, querystart, firsthitchr, firsthitstart, querysequence) = line1.group(1,2, 3, 4, 6, 7, 13)
            (queryname, querychr, arbitraryid, querystart, firsthitstrand, firsthitchr, querysequence, cigarstring) = line1.group(1, 2, 3, 4, 5, 6, 7, 10)
            if not querysequence.endswith(argu.pamsequence):
                queryreversed = Seq(querysequence)
                querysequence = str(queryreversed.reverse_complement())
            #print (cigarstring)
            gc_content = float((querysequence.count('G') + querysequence.count('C'))) / len(querysequence) * 100
            line2 = re.findall("(.*?),([-+])(\d.*?),(\w*.*?|\d*.*?),(\d.*?)\;", str(cigarstring))
            counthits = countoffhits = 1
            bestwindow = []
            inwindscores = []
            outwindscores = []
            #print (len(line2))
            atleastonecountgg = 0
            queryid = str(queryname) + "_" + str(querychr) + "_" + str(arbitraryid) + "_" + str(querystart)
            eachlinedataframe = pd.DataFrame(columns=['secondaryhitschr','secondaryhitsstart','secondaryhitsend','score','sequence','queryname','Totalhitsinalignment'])
            if len(line2) >= int(argu.minhits):
                for eachtuple in line2:
                    secondaryhitschr = str(eachtuple[0])
                    secondaryhitsstrand = str(eachtuple[1])
                    secondaryhitsstart = int(eachtuple[2])
                    secondaryhitpattern = eachtuple[3]
                    secondaryhitmismatch = eachtuple[4]
                    #print (secondaryhitpattern)

                    (length, score, ggfound,forwardseq,revcomplementseq) = checkpam(argu, secondaryhitschr, secondaryhitsstart, secondaryhitpattern, secondaryhitsstrand, getgenome, querysequence,secondaryhitmismatch)
                    if ggfound > 0:
                        atleastonecountgg = atleastonecountgg + 1
                        ##### chromosome should be same...
                        ## create a table
                        #new_row = pd.DataFrame([[secondaryhitschr,secondaryhitsstart,score]],columns=['secondaryhitschr','secondaryhitsstart','score'])
                        new_row = {'secondaryhitschr':secondaryhitschr,'secondaryhitsstart':secondaryhitsstart,'secondaryhitsend':secondaryhitsstart+23, 'score':score, 'sequence':querysequence, 'queryname': queryid, 'Totalhitsinalignment':len(line2)}
                        #print (new_row)
                        #new_row = pd.DataFrame({'secondaryhitschr':secondaryhitschr,'secondaryhitsstart':secondaryhitsstart,'score':score})
                        eachlinedataframe = eachlinedataframe.append(new_row,ignore_index=True)
                        #print(eachlinedataframe)
                        #print ("Inside ggfound >0 loop")
                if (atleastonecountgg >= int(argu.minhits)):
                    #print ("Total number of filtered hits with gg")
                    #print (atleastonecountgg)
                    pd.set_option('display.max_rows', 10)
                    eachlinedataframe['Totalhits'] = eachlinedataframe.apply(lambda row: atleastonecountgg, axis=1)
                    eachlinedataframe = eachlinedataframe.sort_values(['secondaryhitschr', 'secondaryhitsstart', 'secondaryhitsstart'],ascending=[True, True, True])
                    #print (eachlinedataframe)
                    print("Outsideloop")
                    bedhitsinfile = splitinputfile + "_filteredhits.bed"
                    eachlinedataframe.to_csv(bedhitsinfile, sep="\t", index=False, header=False,mode='w+')
                    eachlinedataframe1 = eachlinedataframe
                    #print(eachlinedataframe)
                    allchr = eachlinedataframe[['secondaryhitschr', 'secondaryhitsstart']].groupby('secondaryhitschr').secondaryhitsstart.agg('max').reset_index()
                    allchrmin = eachlinedataframe1[['secondaryhitschr','secondaryhitsstart']].groupby('secondaryhitschr').secondaryhitsstart.agg('min')
                    allchrnew = pd.merge(allchrmin, allchr, on='secondaryhitschr')
                    bedtoolswindowinfile = splitinputfile + "_filteredhitsmaxmin.bed"

                    allchrnew.to_csv(bedtoolswindowinfile, sep="\t", index=False, header=False, mode='w+')
                    windowedfile = splitinputfile + "_windowed.txt"
                    filemakewindowsin = open(os.path.join(argu.workingdirectory,windowedfile), 'w+')

                    filemapoverlapout = open(os.path.join(argu.workingdirectory,splitinputfile+"overlap.txt"), 'w+')
                    #overlapfile = open("overlap.txt", "r")
                    filemapoverlapfile = splitinputfile+"overlap.txt"
                    #print (filemapoverlapfile)
                    p1 = subprocess.Popen(['bedtools', 'makewindows', '-b', str(bedtoolswindowinfile), '-w', str(argu.windowsize), '-s', str(argu.slidinglength)],stdout=filemakewindowsin)
                    p1.communicate()
                    p2 = subprocess.Popen(['bedtools', 'map', '-a', str(windowedfile), '-b', str(bedhitsinfile),'-c', "4,4,5,6,7", '-o', "count,sum,distinct,distinct,distinct"],stdout=filemapoverlapout)
                    p2.communicate()
                    data = pd.read_csv(filemapoverlapfile, sep="\t", names=['chr', 'start', 'end', 'hitsinwindow', 'score','sequence', 'hitid', 'Totalhits'],dtype = str)
                    data['hitsinwindow'] = data['hitsinwindow'].astype('int')
                    data1 = data.sort_values(['hitsinwindow'], ascending=[False]).head(argu.windownumbers)
                    inwindowtarget = data1['hitsinwindow'].apply(pd.to_numeric).sum()
                    data1['Totalhits'] = data1['Totalhits'].astype('int')
                    data1['hitsinwindow'] = data1['hitsinwindow'].astype('int')
                    TotalHitsforthatRNA = data1['Totalhits'].astype('int').iloc[0]
                    data1['off-targets-hits'] = data1.apply(lambda row: TotalHitsforthatRNA-inwindowtarget, axis=1)
                    data1.to_csv(fileoutstd, sep="\t", index=False, header=True)
                    #print (inwindowtarget)
                    #print(data1)

                #f.close()
                #overlapout.close()
def multisgrna(argu):
    multisgrnafile = "crispr_broad_multisgrna.xls"
    filemultisgrnain = open(os.path.join(argu.workingdirectory, multisgrnafile), 'w+')
    p2 = subprocess.Popen(['bedtools', 'intersect', '-a', str(argu.crisprbroadresfile), '-b', str(argu.crisprbroadresfile), '-wao'], stdout=filemultisgrnain)
    p2.communicate()
