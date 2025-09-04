# Quiz Management System

A modern, feature-rich quiz management system built with Flask and PostgreSQL, featuring a beautiful responsive UI powered by Tailwind CSS.

## ✨ Features

### 🎯 Core Functionality
- **User Authentication**: Secure login/register system with role-based access
- **Quiz Creation**: Admin panel for creating and managing quizzes
- **Quiz Taking**: Interactive quiz interface with progress tracking
- **Results & Analytics**: Detailed performance insights and statistics
- **User Management**: Admin tools for managing users and roles

### 🎨 User Experience
- **Responsive Design**: Works perfectly on all devices
- **Modern UI**: Beautiful interface with smooth animations
- **Progress Tracking**: Visual progress bars and navigation
- **Real-time Feedback**: Immediate results and performance insights

### 🔐 Security Features
- **Password Hashing**: Secure password storage with bcrypt
- **Session Management**: Secure user sessions
- **Role-based Access**: Different interfaces for admins and students
- **Input Validation**: Form validation and sanitization

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- PostgreSQL database
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd quiz-management-system
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   # Database Configuration
   DB_HOST=localhost
   DB_NAME=quiz_db
   DB_USER=postgres
   DB_PASSWORD=your_password_here
   DB_PORT=5432
   
   # Flask Configuration
   SECRET_KEY=your-secret-key-here-change-this-in-production
   FLASK_ENV=development
   FLASK_DEBUG=True
   ```

4. **Set up PostgreSQL database**
   ```sql
   CREATE DATABASE quiz_db;
   CREATE USER quiz_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE quiz_db TO quiz_user;
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the system**
   - Open your browser and go to `http://localhost:5000`
   - Use the demo admin account: `admin` / `admin123`

## 👥 User Roles

### Admin
- Create and manage quizzes
- Add/edit/delete questions
- View all user attempts and statistics
- Manage user accounts
- Set passing scores and question points

### Student
- View available quizzes
- Take quizzes with interactive interface
- View detailed results and performance
- Track learning progress
- Access quiz history

## 🎯 Quiz Features

### Question Types
- **Multiple Choice**: Standard multiple choice questions
- **True/False**: Simple true/false questions

### Quiz Management
- **Dynamic Creation**: Add/remove questions on the fly
- **Point System**: Assign different point values to questions
- **Passing Scores**: Customizable passing thresholds
- **Real-time Preview**: See quiz structure as you build

## 🎨 UI Components

### Design System
- **Tailwind CSS**: Modern utility-first CSS framework
- **Responsive Grid**: Adaptive layouts for all screen sizes
- **Color Schemes**: Consistent color palette and theming
- **Typography**: Clear, readable text hierarchy

### Interactive Elements
- **Progress Bars**: Visual quiz progress indicators
- **Navigation**: Easy question-to-question navigation
- **Modals**: Clean dialog interfaces for actions
- **Animations**: Smooth transitions and hover effects

## 🔧 Technical Details

### Backend
- **Flask**: Lightweight Python web framework
- **PostgreSQL**: Robust relational database
- **SQLAlchemy**: Database ORM and migrations
- **Bcrypt**: Secure password hashing

### Frontend
- **Tailwind CSS**: Utility-first CSS framework
- **Font Awesome**: Comprehensive icon library
- **Vanilla JavaScript**: Lightweight, no framework dependencies
- **Responsive Design**: Mobile-first approach

### Database Schema
- **Users**: Authentication and role management
- **Quizzes**: Quiz metadata and settings
- **Questions**: Question content and options
- **Attempts**: User quiz attempts and scores
- **Answers**: Individual question responses

## 📱 Responsive Design

The system is fully responsive and works seamlessly on:
- Desktop computers
- Tablets
- Mobile phones
- All modern browsers

## 🚀 Deployment

### Production Considerations
- Change the `SECRET_KEY` to a secure random string
- Use environment variables for sensitive configuration
- Set up proper database backups
- Configure HTTPS for production use
- Use a production WSGI server (e.g., Gunicorn)

### Docker Support (Coming Soon)
- Containerized deployment
- Easy scaling and management
- Environment isolation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

If you encounter any issues:
1. Check the documentation
2. Search existing issues
3. Create a new issue with detailed information

## 🔮 Future Enhancements

- [ ] Advanced question types (essay, matching, etc.)
- [ ] Time limits for quizzes
- [ ] Quiz scheduling and availability windows
- [ ] Advanced analytics and reporting
- [ ] API endpoints for external integrations
- [ ] Mobile app support
- [ ] Multi-language support
- [ ] Quiz templates and sharing

---

**Built with ❤️ using modern web technologies**
