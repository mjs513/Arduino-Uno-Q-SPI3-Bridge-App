#ifndef SerialCommand_h
#define SerialCommand_h

#include <Arduino.h>

#define SERIALCOMMAND_BUFFER 64
#define SERIALCOMMAND_MAXCOMMANDLENGTH 16

class SerialCommand {
public:
    SerialCommand();

    void addCommand(const char *command, void (*function)());
    void setDefaultHandler(void (*function)(const char *));
    void readSerial();
    char *next();

private:
    struct SerialCommandCallback {
        char command[SERIALCOMMAND_MAXCOMMANDLENGTH];
        void (*function)();
    };

    SerialCommandCallback *commandList;
    uint8_t commandCount;

    void (*defaultHandler)(const char *);
    char term;
    char delim[4];

    char buffer[SERIALCOMMAND_BUFFER];
    uint8_t bufPos;

    char *last;   // save pointer for tokenizer

    void clearBuffer();

    // our custom tokenizer
    char* tokenize(char* str, const char* delim, char** saveptr);
};

#endif
