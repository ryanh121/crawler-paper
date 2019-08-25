""" 
This script crawls everything (paper, review, all comments) from the OpenReview dataset.
I feel the URL should work directly for the ICLR 2019 dataset:
https://openreview.net/notes?forum=B1e7hs05Km&trash=true
"""

import re 
import time 
import sys   
import json 
import os 
 
reload(sys)   
sys.setdefaultencoding('utf8') 
#import codecs 
import urllib2 
import html2text

# url = 'https://openreview.net/notes?invitation=ICLR.cc%2F2017%2Fworkshop%2F-%2Fsubmission'
# https://openreview.net/notes?invitation=ICLR.cc%2F2019%2FConference%2F-%2FBlind_Submission
# https://openreview.net/notes?invitation=ICLR.cc%2F2018%2FConference%2F-%2FBlind_Submission

#data_path = '/home/srg/xueqing/data/iclr2017workshop/' 
#data_path = '/mnt/d/Research/data/iclr2017workshop/' 
data_path = '/mnt/d/Research/data/iclr2018conference/' 
#data_path = '/mnt/d/Research/data/iclr2019conference/' 

#keylist = [u'replyCount', u'signatures', u'nonreaders', u'forum', u'readers', u'replyto', u'writable', u'tmdate', u'number', u'tcdate', u'content', u'tddate', u'writers', u'invitation', u'id', u'ddate', u'tags']
keylist = [u'signatures', u'nonreaders', u'forum', u'readers', u'replyto', u'tmdate', u'number', u'id', u'content', u'tddate', u'writers', u'details', u'invitation', u'original', u'cdate', u'tcdate', u'ddate']
#content_keylist = [u'title', u'abstract', u'conflicts', u'authorids', u'keywords', u'authors', u'TL;DR', u'pdf']
content_keylist = [u'title', u'abstract', u'paperhash', u'TL;DR', u'_bibtex', u'authorids', u'authors', u'keywords', u'pdf']

regex_title = re.compile('^.*#(?P<title>[^#]*)\[!\[\]\(\/.*$', re.DOTALL)#static/images/pdf_icon_blue.svg)].*$', re.DOTALL)
#regex_abstract = re.compile('^.*Abstract:\*\*(?P<abstract>[^\n]*)\n  \* \*\*(TL|Conflict|Keyword).*$', re.DOTALL)
regex_abstract = re.compile('^.*Abstract:\*\*(?P<abstract>[^\n]*)\n.*$', re.DOTALL)
#regex_authorid = re.compile('^.*\*\*Authorids:\*\*(?P<authorid>[^\*\n]*)\n.*$', re.DOTALL)
regex_authorid = re.compile('\)\n\n###.(?P<authorid>[^\d]*)\n.*$', re.DOTALL)
#regex_tldr = re.compile('^.*DR:\*\*(?P<tldr>[^\*\n]*)\n  \* \*\*(Keywords|Conflicts|Authorid).*$', re.DOTALL)
regex_tldr = re.compile('^.*DR:\*\*(?P<tldr>[^\n]*)\n.*$', re.DOTALL)

with open(data_path + 'cache_json.json', 'r') as fin:
        json_result = json.load(fin)

def dfs_tree(rootid, nodeid, prefix, fout, subsubpath, id2children, id2signature, id2tmdate, id2tcdate, id2content):
        signature = id2signature[nodeid]
        content = id2content[nodeid]
        content_title = content[u'title']
        flag = 'comment'
        if u'decision' in content:
                try:
                	content_body = content[u'comment']
                except KeyError:
                        content_body = ''
                flag = 'meta_review'
        elif u'recommendation' in content.keys():
                try:
                	content_body = content[u'metareview']
                except KeyError:
                        content_body = ''
                flag = 'meta_review'
        elif u'comment' in content:
                content_body = content[u'comment']
        elif u'question' in content:
                content_body = content[u'question']
                flag = 'question'
        elif u'review' in content:
                content_body = content[u'review']
                flag = 'review'
        else:
                raise ValueError('undefined type')
        tmdate = id2tmdate[nodeid]
        tcdate = id2tcdate[nodeid]
        if flag == 'meta_review':
                fout.write(prefix + 'nodeid:\t' + nodeid + '\t(meta_review)\n')
        elif flag == 'review':
                fout.write(prefix + 'nodeid:\t' + nodeid + '\t(review)\n')
        else:
                fout.write(prefix + 'nodeid:\t' + nodeid + '\n')
        fout.write(prefix + 'signature:\t' + signature + '\n')
        fout.write(prefix + 'tmdate:\t' + str(tmdate) + '\n')
        fout.write(prefix + 'tcdate:\t' + str(tcdate) + '\n')
        fout.write(prefix + 'content title:\t' + content_title + '\n')
        fout.write(prefix + 'content body:\t' + repr(content_body) + '\n')
        try:
                children = id2children[nodeid]
                for child in children:
                        dfs_tree(rootid, child, prefix + '\t', fout, subsubpath, id2children, id2signature, id2tmdate, id2tcdate, id2content)
        except KeyError:
                return

def write_meta(sub_path, resulti):
        fout = open(sub_path + 'meta', 'w')
        for j in range(0, len(keylist)):
                keyj = keylist[j]
                try:
                        valuej = resulti[keyj]
                except KeyError:
                        valuej = ''
                        print resulti[u'number'], ' not contain ', keyj
                if keyj == 'content':
                        fout.write(keyj + '\n')
                        for k in range(0, len(content_keylist)):
                                subkeyk = content_keylist[k]
                                try:
                                        subvaluek = valuej[subkeyk]
                                except KeyError:
                                        subvaluek = ''
                                        print resulti[u'number'], ' not contain ', subkeyk
                                if subkeyk in set(['authorids', 'keywords', 'authors']):
                                        fout.write('\t' + str(subkeyk) + '\t')
                                        for l in range(0, len(subvaluek)):
                                                fout.write(str(subvaluek[l]) + ',')
                                        fout.write('\n')
                                else:
                                        fout.write('\t' + str(subkeyk) + '\t' + str(subvaluek) + '\n')
                else:
                        fout.write(str(keyj) + '\t' + str(valuej) + '\n')
        fout.close()

def write_abstract(sub_path, forumcode):
	fout = open(sub_path + 'abstract', 'w')
	suburl = 'https://openreview.net/forum?id=' + forumcode + '&noteId=' + forumcode
	page = urllib2.urlopen(suburl)
	time.sleep(5)
	html_content = page.read()      
	rendered_content = html2text.html2text(html_content)
	result_title = regex_title.search(rendered_content)
	result_abstract = regex_abstract.search(rendered_content)
	result_authorid = regex_authorid.search(rendered_content)
	result_tldr = regex_tldr.search(rendered_content)
        #print map(type,[result_title,result_abstract,result_authorid,result_tldr])
	title = result_title.group('title').replace('\n', ' ').lstrip().rstrip()
	# if len(title) < 4 or len(title) > 150:
	#         print title
	#         sys.exit(1)
	abstract = result_abstract.group('abstract').lstrip()
	authorid = result_authorid.group('authorid').replace('\n', ' ').lstrip().rstrip()
	fout.write('title:\t' + title + '\nabstract:\t' + abstract + '\nauthorid:\t' + authorid)
        #print result_tldr,'\n',type(result_tldr),'\n'
	if result_tldr:
		 tldr = result_tldr.group('tldr').lstrip()
	         fout.write('\ntldr:\t' + tldr)
	else:
		if 'TL;DR' in rendered_content:
  			raise ValueError('did not catch tldr')
	fout.close()

def write_pdf(sub_path, forumcode):
        suburl = 'https://openreview.net/pdf?id=' + forumcode
        page = urllib2.urlopen(suburl)
        time.sleep(5)
        fout = open(sub_path + "paper.pdf", 'w')
        fout.write(page.read())
        fout.close()

def write_first_version(sub_path, forumcode):
        jsonurl = "https://openreview.net/references?referent=" + forumcode + "&original=true"
        first_version_id = str(json.loads(urllib2.urlopen(jsonurl).read())[u'references'][-1][u'id'])
        suburl = "https://openreview.net/references/pdf?id=" + first_version_id
        page = urllib2.urlopen(suburl)
        time.sleep(5)
        fout = open(sub_path + "first_version.pdf", 'w')
        fout.write(page.read())
        fout.close()

def write_review(sub_path, forumcode):
        suburl = 'https://openreview.net/notes?forum=' + forumcode + '&trash=true'
        subpage = urllib2.urlopen(suburl)
        time.sleep(5)
        subjsonresult = json.loads(subpage.read())['notes']
	if len(subjsonresult) == 1:
		return
	subsubpath = sub_path + 'review/'
        if not os.path.exists(subsubpath):
                os.makedirs(subsubpath)
        ratings = [''] * 20
        titles = [''] * 20
        reviews = [''] * 20
        confidences = [''] * 20
        maxindex = -1
        invalidjset = set([])
        for j in range(0, len(subjsonresult)):
                #print j,len(subjsonresult)
                try:
                        signature = subjsonresult[j][u'signatures'][0]
                except IndexError:
                        # first check if all fields are 0
                        if subjsonresult[j][u'signatures'] == [] and subjsonresult[j][u'content'][u'authors'] == [] and subjsonresult[j][u'writers'] == [] and (u'title' not in subjsonresult[j][u'content']):
                                print subjsonresult[j][u'id'], 'is empty', i, forumcode, resulti[u'number']
                                invalidjset.add(j)
                                continue
                        else:
                                raise ValueError('empty content ' + subjsonresult[j][u'id']  + ' '+ str(i) + ' ' + forumcode)
                subcontent = subjsonresult[j][u'content']
                if u'rating' in subcontent and len(signature) > 13 and signature[-13:-1] == 'AnonReviewer':
                        index = int(signature[-1]) - 1
                        maxindex = max(maxindex, index + 1)
                        ratings[index] = subcontent[u'rating']
                        titles[index] = subcontent[u'title']
                        reviews[index] = subcontent[u'review']
                        try:
                                confidences[index] = subcontent[u'confidence']
                        except KeyError:
                                print forumcode, ' Reviewer ', index + 1, ' not confidence'
                                confidences[index] = '-1'
                if u'decision' in subcontent:
                        metatitle = subcontent[u'title']
                        metadecision = subcontent[u'decision']
			try:
                        	metacomment = subcontent[u'comment']
				print forumcode
			except KeyError:
				metacomment = ''
                #print subcontent.keys()
                if u'recommendation' in subcontent.keys():
                        metatitle = subcontent[u'title']
                        metadecision = subcontent[u'recommendation']
			try:
                        	metacomment = subcontent[u'metareview']
				print forumcode
			except KeyError:
				metacomment = ''
        for j in range(0, maxindex):
                if ratings[j] == '':
                        continue
                fout = open(subsubpath + str(j + 1), 'w')
                fout.write('rating:\t' + ratings[j] + '\n')
                fout.write('confident:\t' + confidences[j] + '\n')
                fout.write('title:\t' + titles[j] + '\n')
                fout.write('review:\t' + reviews[j] + '\n')
                fout.close()
        fout = open(subsubpath + 'meta', 'w')
        #fout.write('decision:\t' + metadecision + '\n')
        try:
                fout.write('decision:\t' + metadecision + '\n')
        except UnboundLocalError:
                fout.write('decision:\t' + '\n')
        fout.write('title:\t' + metatitle + '\n')
	fout.write('review:\t' + reviews[j] + '\n')
        fout.close()
        fout = open(subsubpath + 'meta', 'w')
        fout.write('decision:\t' + metadecision + '\n')
        fout.write('title:\t' + metatitle + '\n')
        fout.write('comment:\t' + metacomment + '\n')
        fout.close()
        subsubpath = sub_path + 'discussion_all/'
        if not os.path.exists(subsubpath):
                os.makedirs(subsubpath)
        id2children = {}
        id2signature = {}
        id2tmdate = {}
        id2tcdate = {}
        id2content = {}
        for j in range(0, len(subjsonresult)):
                if j in invalidjset:
                        continue
                thisid = subjsonresult[j][u'id']
                # replyto = subjsonresult[j][u'replyto']
                # if replyto == None:
                #         continue
                try:
                        replyto = subjsonresult[j][u'replyto']
                except KeyError:
                        replyto = None
                if replyto == None:
                        continue
                signature = subjsonresult[j][u'signatures'][0]
                content = subjsonresult[j][u'content']
                tmdate = subjsonresult[j][u'tmdate']
                tcdate = subjsonresult[j][u'tcdate']
                id2children.setdefault(replyto, set([]))
                id2children[replyto].add(thisid)
                id2signature[thisid] = signature
                id2content[thisid] = content
                id2tmdate[thisid] = tmdate
                id2tcdate[thisid] = tcdate
        rootid = forumcode
        children = id2children[rootid]
        for child in children:
                fout = open(subsubpath + child, 'w')
                dfs_tree(rootid, child, '', fout, subsubpath, id2children, id2signature, id2tmdate, id2tcdate, id2content)
                fout.close()

# len(json_result['notes'])
for i in range(0, len(json_result['notes'])):
	print 'crawling', i
	resulti = json_result['notes'][i]
        sub_path = data_path + str(resulti[u'number']) + '/'
        print resulti[u'number']
        if not os.path.exists(sub_path):
                os.makedirs(sub_path)
        # write_meta(sub_path, resulti)
        # print 'meta finished'
	forumcode = resulti[u'forum']
        print 'https://openreview.net/notes?forum=' + forumcode + '&trash=true'
	# write_abstract(sub_path, forumcode)
        # print 'abstract finished'
	# write_pdf(sub_path, forumcode)
        # print 'pdf finished'
	# write_review(sub_path, forumcode)
        # print 'review finished'
        write_first_version(sub_path,forumcode)
        print 'first version finished'
