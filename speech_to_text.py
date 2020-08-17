import xml.etree.ElementTree as XmlElementTree
import httplib2
import uuid
from config import config

### consts
HOST = '***'
PATH = '/***_xml'              # path to XML
CHUNK_SIZE = 1024 ** 2         # defining a chunk of 2KiB units of memory


### define function that converts speech into text
# API_KEY are taken from config
def speech_to_text(filename=None, bytes=None, request_id=uuid.uuid4().hex, topic='notes', lang='ru-RU', key=API_KEY):

    if filename:                                                          # if filename not None
        with open(filename, 'br') as file:                                # open file in binary format for reading
            bytes = file.read()                                           # read bytes
    if not bytes:
        raise Exception('Neither file name nor bytes provided.')          # raise exception if bytes are still None

    # converting bytes to a new format
    bytes = convert_to_pcm16b16000r(in_bytes=bytes)

    ### forming the request url
    # request_id is a random UUID as a 32-character hexadecimal string
    url = PATH + '?uuid=%s&key=%s&topic=%s&lang=%s' % (request_id, key, topic, lang)

    # read a block of bytes and put into collection
    chunks = read_chunks(CHUNK_SIZE, bytes)

    # setting connection and forming a request
    connection = httplib2.HTTPConnectionWithTimeout(HOST)

    connection.connect()                                                  # set connection
    connection.putrequest('POST', url)                                    # create request
    connection.putheader('Transfer-Encoding', 'chunked')                  # indicate that data in chunks with fixed size, no need specify all Content-Length
    connection.putheader('Content-Type', 'audio/x-pcm;bit=16;rate=16000') # linear PCM with 16,000 Hz sampling rate and 16-bit quantization
    connection.endheaders()                                               # send a blank line, the end of the headers

    # sending bytes in blocks (chunks)
    for chunk in chunks:
        connection.send(('%s\r\n' % hex(len(chunk))[2:]).encode())       # send chunk size
        connection.send(chunk)                                           # send chunk (content)
        connection.send('\r\n'.encode())                                 # send CRLF separator

    connection.send('0\r\n\r\n'.encode())                                # finally send NUL and two CRLF separators

    ### server response processing
    response = connection.getresponse()                                  # get response

    if response.code == 200:                                             # if status code is 200
        response_text = response.read()                                  # read response body
        xml = XmlElementTree.fromstring(response_text)                   # build xml tree from response body

        if int(xml.attrib['success']) == 1:                              # if xml tree has attribute success with 'true'
            max_confidence = - float("inf")                              # set as a minus infinity
            text = ''

            for child in xml:                                            # loop for analyzing child attribute 'confidence'
                if float(child.attrib['confidence']) > max_confidence:
                    text = child.text
                    max_confidence = float(child.attrib['confidence'])

            # return text derived from speech if max_confidence changed
            if max_confidence != - float("inf"):
                return text
            else:
                raise SpeechException('No text found.\n\nResponse:\n%s' % (response_text))
        else:
            raise SpeechException('No text found.\n\nResponse:\n%s' % (response_text))
    else:
        raise SpeechException('Unknown error.\nCode: %s\n\n%s' % (response.code, response.read()))


### empty class for exceptions handling, extends Exception
class SpeechException(Exception):
    pass
