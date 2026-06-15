#include "SerialCommand.h"
#include <string.h>
#include <ctype.h>

SerialCommand::SerialCommand()
    : commandList(NULL),
      commandCount(0),
      defaultHandler(NULL),
      term('\n'),
      last(NULL)
{
    strcpy(delim, " ");
    clearBuffer();
}

void SerialCommand::addCommand(const char *command, void (*function)()) {
    commandList = (SerialCommandCallback*) realloc(
        commandList,
        (commandCount + 1) * sizeof(SerialCommandCallback)
    );

    char *dst = commandList[commandCount].command;
    size_t len = strlen(command);

    for (size_t i = 0; i < len && i < SERIALCOMMAND_MAXCOMMANDLENGTH - 1; i++) {
        char c = command[i];
        if (c >= 'a' && c <= 'z')
            c &= ~0x20;  // uppercase
        dst[i] = c;
    }
    dst[len] = '\0';

    commandList[commandCount].function = function;
    commandCount++;
}

void SerialCommand::setDefaultHandler(void (*function)(const char *)) {
    defaultHandler = function;
}

void SerialCommand::readSerial() {
    while (Serial.available() > 0) {
        char inChar = Serial.read();

        if (inChar == term) {
            char *command = tokenize(buffer, delim, &last);

            if (command != NULL) {
                // uppercase command
                for (char *p = command; *p; p++) {
                    if (*p >= 'a' && *p <= 'z')
                        *p &= ~0x20;
                }

                bool matched = false;

                for (uint8_t i = 0; i < commandCount; i++) {
                    if (strncmp(command, commandList[i].command,
                                SERIALCOMMAND_MAXCOMMANDLENGTH) == 0) {
                        (*commandList[i].function)();
                        matched = true;
                        break;
                    }
                }

                if (!matched && defaultHandler != NULL) {
                    defaultHandler(command);
                }
            }

            clearBuffer();
        }
        else if (isprint(inChar)) {
            if (bufPos < SERIALCOMMAND_BUFFER - 1) {
                if (inChar >= 'a' && inChar <= 'z')
                    inChar &= ~0x20;  // uppercase
                buffer[bufPos++] = inChar;
                buffer[bufPos] = '\0';
            }
        }
    }
}

void SerialCommand::clearBuffer() {
    buffer[0] = '\0';
    bufPos = 0;
    last = NULL;
}

char *SerialCommand::next() {
    return tokenize(NULL, delim, &last);
}

// ---------------------------------------------------------------------------
// Custom tokenizer (replaces strtok_r)
// ---------------------------------------------------------------------------
char* SerialCommand::tokenize(char* str, const char* delim, char** saveptr) {
    char* start;

    if (str != NULL) {
        start = str;
    } else if (*saveptr != NULL) {
        start = *saveptr;
    } else {
        return NULL;
    }

    // skip leading delimiters
    while (*start && strchr(delim, *start)) {
        start++;
    }

    if (*start == '\0') {
        *saveptr = NULL;
        return NULL;
    }

    char* end = start;

    while (*end && !strchr(delim, *end)) {
        end++;
    }

    if (*end) {
        *end = '\0';
        *saveptr = end + 1;
    } else {
        *saveptr = NULL;
    }

    return start;
}
