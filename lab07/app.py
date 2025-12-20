import os
import time
import json
import base64
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

# Імпорт наших локальних модулів
import crypto_module
import stego_module

console = Console()

class Lab7System:
    def __init__(self):
        self.stats = []

    def log_stat(self, stage, time_taken, size_info):
        self.stats.append([stage, f"{time_taken:.4f} с", size_info])

    def run_protection(self, user, birth, file_path, cover_img):
        console.print(Panel(f"[bold cyan]🔒 ЕТАП 1: ЗАХИСТ ({file_path})[/bold cyan]"))
        
        # 1. Читання файлу
        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()
        except FileNotFoundError:
            console.print("[bold red]Файл не знайдено![/bold red]")
            return None

        # --- КРОК А: ПІДПИС (RSA) ---
        t0 = time.time()
        keys = crypto_module.generate_rsa_keys(user, birth)
        signature = crypto_module.sign_data(file_bytes, keys.private)
        t1 = time.time()
        
        # Формуємо пакет: {ім'я файлу, контент(base64), підпис}
        payload = {
            "filename": os.path.basename(file_path),
            "content": base64.b64encode(file_bytes).decode('utf-8'),
            "signature": signature
        }
        json_str = json.dumps(payload)
        
        self.log_stat("Цифровий підпис (RSA)", t1 - t0, f"Підпис: {len(signature)} байт")
        console.print("[green]✔ Файл підписано[/green]")

        # --- КРОК Б: ШИФРУВАННЯ (AES) ---
        t0 = time.time()
        aes = crypto_module.AESCipher(user, birth)
        encrypted_data = aes.encrypt(json_str)
        t1 = time.time()
        
        self.log_stat("Шифрування (AES)", t1 - t0, f"Дані: {len(encrypted_data)} байт")
        console.print("[green]✔ Дані зашифровано[/green]")

        # --- КРОК В: СТЕГАНОГРАФІЯ (LSB) ---
        t0 = time.time()
        output_img = "protected_result.png"
        stego_module.hide_lsb(cover_img, output_img, encrypted_data)
        t1 = time.time()
        
        final_size = os.path.getsize(output_img)
        self.log_stat("Стеганографія (LSB)", t1 - t0, f"Файл: {final_size/1024:.2f} КБ")
        console.print(f"[green]✔ Дані сховано в {output_img}[/green]")
        
        return output_img

    def run_recovery(self, user, birth, stego_img):
        console.print("\n" + "="*40 + "\n")
        console.print(Panel(f"[bold magenta]🔓 ЕТАП 2: ВІДНОВЛЕННЯ ({stego_img})[/bold magenta]"))

        # --- КРОК А: ВИТЯГУВАННЯ ---
        try:
            encrypted_data = stego_module.extract_lsb(stego_img)
            console.print("[green]✔ Дані витягнуто з картинки[/green]")
        except Exception as e:
            console.print(f"[red]Помилка стеганографії: {e}[/red]")
            return

        # --- КРОК Б: ДЕШИФРУВАННЯ ---
        try:
            aes = crypto_module.AESCipher(user, birth)
            json_str = aes.decrypt(encrypted_data)
            payload = json.loads(json_str)
            console.print("[green]✔ Дані розшифровано[/green]")
        except Exception as e:
            console.print(f"[bold red]ПОМИЛКА: Невірний пароль або пошкоджені дані![/bold red]")
            return

        # --- КРОК В: ПЕРЕВІРКА ПІДПИСУ ---
        file_bytes = base64.b64decode(payload['content'])
        signature = payload['signature']
        
        keys = crypto_module.generate_rsa_keys(user, birth)
        is_valid = crypto_module.verify_signature_data(file_bytes, signature, keys.public)

        restored_name = "restored_" + payload['filename']
        with open(restored_name, "wb") as f:
            f.write(file_bytes)

        console.print(f"Файл збережено як: [bold]{restored_name}[/bold]")

        if is_valid:
            console.print(Panel("[bold green]✅ ПІДПИС ВІРНИЙ! Файл автентичний.[/bold green]"))
        else:
            console.print(Panel("[bold red]⛔ УВАГА! Файл було змінено або підроблено![/bold red]"))

    def show_table(self):
        table = Table(title="📊 Аналітика ефективності")
        table.add_column("Етап", style="cyan")
        table.add_column("Час", style="magenta")
        table.add_column("Розмір/Інфо", style="green")
        
        for row in self.stats:
            table.add_row(*row)
        console.print(table)

if __name__ == "__main__":
    # Створюємо тестові файли, якщо їх немає
    if not os.path.exists("secret_doc.txt"):
        with open("secret_doc.txt", "w", encoding='utf-8') as f:
            f.write("Це секретний текст для Лабораторної роботи №7. Паролі: 12345.")
            
    if not os.path.exists("cover.png"):
        # Створимо просту картинку, якщо її немає (білий квадрат)
        from PIL import Image
        img = Image.new('RGB', (800, 600), color = 'white')
        img.save('cover.png')

    # Інтерфейс
    console.print("[bold yellow]Лабораторна робота №7: Комплексний захист[/bold yellow]")
    
    user = Prompt.ask("Введіть ваше ім'я", default="Student")
    birth = Prompt.ask("Дата народження (ДД.ММ.РРРР)", default="01.01.2000")
    
    system = Lab7System()
    
    # Запуск захисту
    stego_file = system.run_protection(user, birth, "secret_doc.txt", "cover.png")
    
    if stego_file:
        system.show_table()
        
        # Симуляція передачі файлу...
        if Prompt.ask("\nСпробувати відновити файл?", choices=["y", "n"], default="y") == "y":
            # Можна ввести інші дані, щоб перевірити помилку
            check_user = Prompt.ask("Введіть ім'я для розшифровки", default=user)
            system.run_recovery(check_user, birth, stego_file)