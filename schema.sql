-- Database schema for Noi That Bao Khang
-- Target Database: Microsoft SQL Server (MS SQL)

USE master;
GO

-- 1. Create Database if not exists
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'noithatbaokhang_db')
BEGIN
    CREATE DATABASE noithatbaokhang_db;
END;
GO

USE noithatbaokhang_db;
GO

-- 2. Table Users
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Users]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[Users] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [username] NVARCHAR(50) NOT NULL UNIQUE,
        [password] NVARCHAR(255) NOT NULL,
        [fullname] NVARCHAR(100) DEFAULT NULL,
        [phone] NVARCHAR(20) DEFAULT NULL,
        [role] NVARCHAR(20) DEFAULT N'customer', -- 'admin' or 'customer'
        [created_at] DATETIME DEFAULT GETDATE()
    )
END;
GO

-- 3. Table Categories
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Categories]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[Categories] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [name] NVARCHAR(100) NOT NULL,
        [slug] NVARCHAR(100) NOT NULL UNIQUE,
        [parent_id] INT DEFAULT NULL,
        FOREIGN KEY ([parent_id]) REFERENCES [dbo].[Categories] ([id])
    )
END;
GO

-- 4. Table Products
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Products]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[Products] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [code] NVARCHAR(50) NOT NULL UNIQUE,
        [name] NVARCHAR(150) NOT NULL,
        [category_id] INT DEFAULT NULL,
        [price_text] NVARCHAR(100) DEFAULT NULL,
        [original_price] DECIMAL(15, 2) DEFAULT NULL,
        [sale_price] DECIMAL(15, 2) DEFAULT NULL,
        [description] NVARCHAR(MAX) DEFAULT NULL,
        [is_sale] TINYINT DEFAULT 0,
        [created_at] DATETIME DEFAULT GETDATE(),
        FOREIGN KEY ([category_id]) REFERENCES [dbo].[Categories] ([id]) ON DELETE SET NULL
    )
END;
GO

-- 5. Table ProductImages
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ProductImages]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[ProductImages] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [product_id] INT NOT NULL,
        [image_path] NVARCHAR(255) NOT NULL,
        FOREIGN KEY ([product_id]) REFERENCES [dbo].[Products] ([id]) ON DELETE CASCADE
    )
END;
GO

-- 6. Table Orders
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Orders]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[Orders] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [customer_name] NVARCHAR(100) NOT NULL,
        [customer_phone] NVARCHAR(20) NOT NULL,
        [customer_address] NVARCHAR(MAX) NOT NULL,
        [note] NVARCHAR(MAX) DEFAULT NULL,
        [total_amount] DECIMAL(15, 2) DEFAULT 0.00,
        [status] NVARCHAR(50) DEFAULT N'pending', -- 'pending', 'processing', 'completed', 'cancelled'
        [created_at] DATETIME DEFAULT GETDATE()
    )
END;
GO

-- 7. Table OrderItems
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[OrderItems]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[OrderItems] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [order_id] INT NOT NULL,
        [product_id] INT NOT NULL,
        [quantity] INT DEFAULT 1,
        FOREIGN KEY ([order_id]) REFERENCES [dbo].[Orders] ([id]) ON DELETE CASCADE,
        FOREIGN KEY ([product_id]) REFERENCES [dbo].[Products] ([id]) ON DELETE CASCADE
    )
END;
GO

-- 8. Table chat_messages
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[chat_messages]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[chat_messages] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [session_id] NVARCHAR(100) NOT NULL,
        [sender_type] NVARCHAR(20) NOT NULL CHECK ([sender_type] IN ('customer', 'admin')),
        [sender_name] NVARCHAR(100) DEFAULT NULL,
        [message] NVARCHAR(MAX) NOT NULL,
        [is_read] TINYINT DEFAULT 0,
        [created_at] DATETIME DEFAULT GETDATE()
    );
    CREATE INDEX IX_chat_messages_session ON [dbo].[chat_messages] (session_id);
END;
GO

