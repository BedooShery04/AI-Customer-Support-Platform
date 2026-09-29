# AI Customer Support Platform

A full-stack intelligent customer support platform that combines **AI-powered assistance**, **ticket management**, **role-based access control**, and **workflow automation** into a single web application.

The platform is designed to support three types of users—**Customers, Agents, and Administrators**—while using an AI assistant powered by **LangChain + LangGraph + LLMs** to understand requests and perform controlled backend operations through dedicated tools.

---

## 🚀 Features

### 🤖 AI Customer Support Assistant

The platform includes a conversational AI assistant capable of interacting with the support system through backend tools.

Depending on the authenticated user's role, the AI can:

* Answer customer support questions
* Retrieve ticket information
* Check ticket status
* Create ticket drafts
* Propose ticket updates
* Find customers by email
* Create tickets on behalf of customers
* Update ticket priority and status
* Escalate tickets
* Maintain multiple AI conversations
* Store and retrieve chat history
* Rename and delete conversations
* Require explicit confirmation before sensitive ticket operations

The AI workflow is implemented using **LangChain and LangGraph**, with role-specific tools and controlled database access.

---

## 🎫 Ticket Management

The platform provides a complete ticket lifecycle.

### Customers

Customers can:

* Create support tickets
* View their tickets
* View individual ticket details
* Check ticket status
* Chat with the AI assistant
* Propose changes to their own open tickets

### Agents

Agents can:

* View assigned tickets
* View customer information
* View ticket details
* Update ticket priority
* Update ticket status
* Escalate tickets
* Use AI assistance for support operations
* Create ticket drafts on behalf of customers

### Administrators

Administrators can:

* View all tickets
* Manage users
* Manage agents
* View platform statistics
* Manage ticket assignments
* Update ticket status and priority
* Access administrative dashboards
* Delete tickets when required

---

## 👥 Role-Based Access Control

The system implements authentication and authorization using **JWT-based authentication** and role-specific dependencies.

Supported roles:

| Role       | Description                                              |
| ---------- | -------------------------------------------------------- |
| `customer` | Creates and manages their own support tickets            |
| `agent`    | Handles assigned tickets and performs support operations |
| `admin`    | Manages users, agents, tickets, and platform operations  |

User account states include:

| Status      | Description                                    |
| ----------- | ---------------------------------------------- |
| `active`    | Account can access the platform                |
| `suspended` | Account is waiting for administrative approval |
| `inactive`  | Account has been deactivated                   |

Access to protected endpoints is controlled through dependencies such as:

* `get_current_user`
* `require_customer`
* `require_agent`
* `require_admin`

---

## 🧠 AI Architecture

The AI layer is built around a tool-based architecture.

```text
                    ┌─────────────────────┐
                    │      Frontend       │
                    │ HTML/CSS/JavaScript │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    FastAPI API      │
                    │      /ai Router     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     AI Service      │
                    │    AIService        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     LangGraph       │
                    │   Agent Workflow    │
                    └──────────┬──────────┘
                               │
                  ┌────────────┴────────────┐
                  ▼                         ▼
          ┌──────────────┐          ┌──────────────┐
          │     LLM      │          │ AI Tools     │
          │ Google/Groq/ │          │ Ticket/User  │
          │    OpenAI    │          │ Operations   │
          └──────────────┘          └──────┬───────┘
                                           │
                                           ▼
                                  ┌─────────────────┐
                                  │   PostgreSQL    │
                                  └─────────────────┘
```

### Role-aware AI tools

The available tools depend on the authenticated user's role.

#### Customer tools

* Get customer tickets
* Propose ticket creation
* Propose ticket updates
* Get ticket details
* Check ticket status

#### Agent tools

* Find customer by email
* Propose tickets on behalf of a customer
* Get ticket details
* Check ticket status
* Update tickets
* Escalate tickets

#### Admin tools

* Get ticket details
* Check ticket status
* Update tickets

This prevents users from accessing AI operations outside their authorization level.

---

## 🔐 Confirmation-Based AI Operations

Sensitive operations are not applied blindly by the AI.

For example, when a customer asks the AI to modify a ticket, the AI creates a **pending update proposal** instead of immediately changing the database.

```text
Customer Request
       │
       ▼
AI Assistant
       │
       ▼
Generate Proposed Change
       │
       ▼
Pending Ticket Update
       │
       ▼
Customer Confirmation
       │
       ├──── Cancel ────► Discard
       │
       ▼
Confirm
       │
       ▼
Apply Database Change
```

The same approach is used for ticket creation proposals.

This provides an additional safety layer between natural-language AI requests and database mutations.

---

## 💬 Multiple AI Conversations

Users can maintain multiple AI conversations.

The platform supports:

* Creating conversations
* Listing conversations
* Opening a conversation
* Renaming conversations
* Deleting conversations
* Storing conversation messages
* Loading previous conversation history

Each AI chat belongs to its authenticated user.

---

## 🏗️ Backend Architecture

The backend follows a layered architecture built with **FastAPI** and **SQLAlchemy**.

```text
FastAPI Router
      │
      ▼
Dependencies / Authorization
      │
      ▼
Service Layer
      │
      ▼
SQLAlchemy Models
      │
      ▼
PostgreSQL
```

### Backend structure

```text
Backend/
├── app/
│   ├── agent/
│   │   ├── graph.py
│   │   ├── prompts.py
│   │   └── tools.py
│   │
│   ├── database/
│   │   ├── base_class.py
│   │   └── database.py
│   │
│   ├── dependencies/
│   │   ├── auth.py
│   │   └── roles.py
│   │
│   ├── enums/
│   │   ├── ticket.py
│   │   └── user.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── ticket.py
│   │   ├── message.py
│   │   ├── audit_log.py
│   │   ├── ai_chat.py
│   │   ├── ai_chat_message.py
│   │   ├── ai_classification.py
│   │   ├── pending_ticket_draft.py
│   │   └── pending_ticket_update.py
│   │
│   ├── routers/
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── tickets.py
│   │   ├── messages.py
│   │   ├── ai.py
│   │   └── admin.py
│   │
│   ├── schemas/
│   │   └── ...
│   │
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── ticket_service.py
│   │   ├── message_service.py
│   │   └── ai_service.py
│   │
│   ├── main.py
│   └── seed.py
│
├── alembic/
├── pyproject.toml
└── uv.lock
```

---

## 🖥️ Frontend

The frontend is implemented using standard:

* HTML5
* CSS3
* JavaScript

No frontend framework is required.

### Frontend structure

```text
Frontend/
├── admin/
│   ├── dashboard.html
│   ├── agents.html
│   ├── users.html
│   ├── tickets.html
│   └── statistics.html
│
├── agent/
│   ├── dashboard.html
│   ├── assigned-tickets.html
│   ├── ticket-details.html
│   ├── customers.html
│   ├── customer-details.html
│   └── ai-assistant.html
│
├── customer/
│   ├── dashboard.html
│   ├── tickets.html
│   ├── create-ticket.html
│   ├── ticket-details.html
│   └── chatbot.html
│
├── css/
├── js/
├── index.html
├── login.html
├── register.html
└── profile.html
```

---

## 🛠️ Technology Stack

### Backend

* **Python 3.14+**
* **FastAPI**
* **Uvicorn**
* **SQLAlchemy**
* **PostgreSQL**
* **Alembic**
* **Pydantic**
* **Pydantic Settings**

### Authentication & Security

* **JWT**
* **python-jose**
* **Passlib**
* **bcrypt**
* Role-based authorization
* Protected API endpoints

### AI

* **LangChain**
* **LangGraph**
* **Google Gemini integration**
* **Groq integration**
* **OpenAI integration**
* Tool-based AI operations
* Role-aware AI capabilities

### Frontend

* HTML5
* CSS3
* JavaScript
* Fetch API
* Responsive dashboard interfaces

### Development

* **uv**
* **Alembic migrations**
* Git / GitHub

---

## 🗄️ Database

The application uses **PostgreSQL** as its primary database.

The database contains entities for:

* Users
* Tickets
* Messages
* AI conversations
* AI chat messages
* AI classifications
* Audit logs
* Pending ticket creation drafts
* Pending ticket update drafts

Database schema changes are managed through **Alembic migrations**.

---

## 🎟️ Ticket Classification

Tickets support structured metadata including:

### Categories

* Technical Issue
* Account Issue
* Billing
* Product Issue
* General Inquiry

### Priorities

* Low
* Medium
* High
* Critical

### Statuses

* Open
* In Progress
* Waiting for Customer
* Resolved
* Closed

---

## 🔥 Ticket Escalation

Agents can explicitly escalate tickets through the platform.

An escalation changes the ticket priority to:

```text
Critical
```

The operation is also recorded through the audit-log mechanism.

The AI assistant exposes an `escalate_ticket` tool to authorized agents.

---

## 📊 Admin Dashboard

The administrative interface provides management functionality for:

* Users
* Agents
* Tickets
* Ticket assignments
* Platform statistics
* Account status
* Administrative operations

Agent accounts can remain suspended until they are approved by an administrator.

---

## 🔑 Authentication Flow

```text
Register
   │
   ▼
Create User
   │
   ├── Customer ──► Active
   │
   └── Agent ─────► Suspended / Pending Approval
                         │
                         ▼
                    Admin Approval
                         │
                         ▼
                       Active
```

After successful login, the backend returns a JWT access token.

The frontend stores the authentication token and uses it when communicating with protected API endpoints.

---

## 📡 API Overview

The backend exposes RESTful API routes organized by functionality.

### Authentication

```text
POST /auth/register
POST /auth/login
GET  /auth/me
```

### Tickets

```text
POST   /tickets
GET    /tickets
GET    /tickets/my
GET    /tickets/assigned
GET    /tickets/{ticket_id}
PUT    /tickets/{ticket_id}
POST   /tickets/{ticket_id}/escalate
DELETE /tickets/{ticket_id}
```

### AI

The AI router provides endpoints for:

* AI chat
* Chat creation
* Chat history
* Chat management
* AI suggestions
* AI ticket classification
* Pending AI operations
* Confirmation/cancellation workflows

### Users & Administration

Dedicated routers are available for:

```text
/users
/admin
```

with access controlled according to user role.

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/BedooShery04/AI-Customer-Support-Platform.git

cd AI-Customer-Support-Platform
```

---

### 2. Backend setup

Move into the backend directory:

```bash
cd Backend
```

The project uses **uv** for Python dependency management.

Install uv if necessary:

```bash
pip install uv
```

Create the environment and install dependencies:

```bash
uv sync
```

Activate the virtual environment if desired:

### Windows

```powershell
.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

---

## 🔐 Environment Variables

Create a `.env` file inside the `Backend` directory.

Example:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/support_platform

SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

GOOGLE_API_KEY=your-google-api-key
GROQ_API_KEY=your-groq-api-key
OPENAI_API_KEY=your-openai-api-key
```

Only configure the LLM provider(s) used by your deployment.

Do not commit `.env` files or API keys to GitHub.

---

## 🐘 PostgreSQL Setup

Create a PostgreSQL database:

```sql
CREATE DATABASE support_platform;
```

Configure the connection string in `.env`.

Example:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/support_platform
```

---

## 🗃️ Database Migrations

From the `Backend` directory:

```bash
uv run alembic upgrade head
```

To create a new migration:

```bash
uv run alembic revision --autogenerate -m "description"
```

---

## 👤 Seed Development Users

The project includes a seed script for creating development users.

Run:

```bash
uv run python -m app.seed
```

The seed script creates development accounts for an agent and an administrator.

> Change development credentials before using the application in a real deployment.

---

## ▶️ Run the Backend

From `Backend/`:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

The API will be available at:

```text
http://127.0.0.1:8000
```

FastAPI also provides interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

and:

```text
http://127.0.0.1:8000/redoc
```

---

## 🌐 Run the Frontend

The frontend is designed to communicate with the FastAPI backend running on port `8000`.

For local development, serve the `Frontend` directory using a local HTTP server such as **VS Code Live Server**.

The current backend CORS configuration allows:

```text
http://127.0.0.1:5500
```

Therefore, if using VS Code Live Server, make sure it runs on port `5500`.

Then open:

```text
http://127.0.0.1:5500
```

---

## 🔄 Request Flow

### Standard API request

```text
Frontend
   │
   ▼
FastAPI Router
   │
   ▼
Authentication / Authorization
   │
   ▼
Service Layer
   │
   ▼
SQLAlchemy
   │
   ▼
PostgreSQL
```

### AI request

```text
Frontend
   │
   ▼
/ai
   │
   ▼
AIService
   │
   ▼
LangGraph
   │
   ├──────────────► LLM
   │
   └──────────────► Tools
                         │
                         ▼
                    Services
                         │
                         ▼
                    PostgreSQL
```

---

## 🔒 Security Considerations

The application implements several security mechanisms:

* JWT-based authentication
* Password hashing with bcrypt
* Role-based authorization
* Protected API endpoints
* User-owned AI conversations
* Role-specific AI tools
* Controlled database operations
* Explicit confirmation for sensitive AI actions
* Audit logging for important operations

For production deployment, additional hardening should be applied, including:

* Secure secret management
* HTTPS
* Production CORS configuration
* Rate limiting
* Secure cookie/token policies where appropriate
* Database credential management
* API key management
* Monitoring and logging

---

## 📁 Project Architecture

```text
AI-Customer-Support-Platform
│
├── Backend
│   ├── app
│   │   ├── agent
│   │   ├── database
│   │   ├── dependencies
│   │   ├── enums
│   │   ├── models
│   │   ├── routers
│   │   ├── schemas
│   │   ├── services
│   │   ├── main.py
│   │   └── seed.py
│   │
│   ├── alembic
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── uv.lock
│
├── Frontend
│   ├── admin
│   ├── agent
│   ├── customer
│   ├── css
│   ├── js
│   ├── login.html
│   ├── register.html
│   └── profile.html
│
└── README.md
```

---

## 🧪 Development & Testing

The project can be tested through:

* FastAPI Swagger UI
* Frontend user flows
* Customer workflows
* Agent workflows
* Admin workflows
* Authentication scenarios
* Ticket lifecycle scenarios
* AI conversations
* AI tool execution
* Ticket escalation
* Role authorization

Recommended testing order:

```text
1. Database
2. Backend API
3. Authentication
4. Role Authorization
5. Ticket Management
6. AI Chat
7. AI Tools
8. Frontend
9. End-to-End Workflows
```

---

## 🎯 Main Use Cases

### Customer

```text
Register/Login
      │
      ▼
Customer Dashboard
      │
      ├── Create Ticket
      ├── View Tickets
      ├── Track Ticket
      └── AI Assistant
```

### Agent

```text
Login
  │
  ▼
Agent Dashboard
  │
  ├── Assigned Tickets
  ├── Customer Information
  ├── Ticket Management
  ├── AI Assistant
  └── Ticket Escalation
```

### Administrator

```text
Login
  │
  ▼
Admin Dashboard
  │
  ├── User Management
  ├── Agent Management
  ├── Ticket Management
  ├── Assignments
  └── Statistics
```

---

## 📌 Current Project Scope

The repository currently contains:

* Full FastAPI backend
* PostgreSQL integration
* SQLAlchemy ORM
* Alembic migrations
* JWT authentication
* Role-based authorization
* Customer, Agent, and Admin workflows
* Ticket management
* Ticket escalation
* AI conversational assistant
* LangChain integration
* LangGraph-based AI workflow
* Role-specific AI tools
* Multiple AI conversations
* AI chat persistence
* AI ticket classification/suggestion infrastructure
* Pending ticket operation workflows
* Audit logging
* Separate dashboards for each role
* Plain HTML/CSS/JavaScript frontend

---

## 🚧 Future Improvements

Potential improvements include:

* Automated CI/CD pipeline
* Containerized deployment with Docker
* Production cloud deployment
* Advanced observability and monitoring
* Automated backend/frontend tests
* More comprehensive AI evaluation
* Improved ticket analytics
* Email and notification integrations
* More workflow automation
* Advanced reporting and analytics

---

## 👥 Contributors

| Contributor | GitHub |
| ----------- | ------ |
| **Abdurrahman Sherif** | [@BedooShery04](https://github.com/BedooShery04) |
| **Hoda Mahmoud** | [@HodaMahmoud111](https://github.com/HodaMahmoud111) |
| **Abdurrahman Antar** | [@abdoantaaaar](https://github.com/abdoantaaaar)
---

## 📄 License

This project is currently intended as an academic/software engineering project.

Add an explicit open-source license to the repository if redistribution or modification by third parties is intended.
