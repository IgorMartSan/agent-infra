from processor import process_agent_message

EXIT_COMMANDS = {"sair", "exit", "quit"}


def main() -> None:
    print("Chat iniciado. Digite 'sair' para encerrar.\n")

    while True:
        try:
            user_input = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando chat.")
            return

        if user_input.lower() in EXIT_COMMANDS:
            print("Encerrando chat.")
            return

        if not user_input:
            continue

        result = process_agent_message({"message": user_input})
        print(f"Gemma 4 Agent: {result['response']}\n")


if __name__ == "__main__":
    main()
