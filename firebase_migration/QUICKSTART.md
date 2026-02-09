# 🚀 Firebase Quickstart - 5 Minutes to Deploy

## The Fastest Path to Production

### Step 1: Create Firebase Project (2 min)
1. Go to https://console.firebase.google.com/
2. Click "Add project"
3. Name it: `clinical-todo-viewer`
4. Disable Google Analytics
5. Click "Create"

### Step 2: Run Setup Script (2 min)
```bash
cd firebase_migration
./setup.sh
```

The script will:
- ✓ Check prerequisites
- ✓ Login to Firebase
- ✓ Extract your HTML
- ✓ Initialize Firebase
- ✓ Configure API keys
- ✓ Deploy your app

**When prompted for API keys, enter:**
- Your Pinecone API key
- Your OpenAI API key

### Step 3: Upload Patient Data (1 min)

1. **Get your service account key:**
   - Go to Firebase Console → Project Settings
   - Service Accounts tab
   - Click "Generate new private key"
   - Save as `scripts/serviceAccountKey.json`

2. **Upload data:**
   ```bash
   cd scripts
   pip install firebase-admin
   python3 upload_patients.py
   ```

### Step 4: Access Your App! (instant)

Your app is now live at:
```
https://YOUR_PROJECT_ID.web.app
```

## That's It! 🎉

Your app is now running on Firebase with:
- ✅ Global CDN hosting
- ✅ Serverless backend
- ✅ Scalable database
- ✅ All features working
- ✅ Running on free tier

## Troubleshooting

**"Firebase CLI not found"**
```bash
npm install -g firebase-tools
```

**"Python not found"**
- Install Python 3.9+ from python.org

**"Permission denied"**
```bash
chmod +x setup.sh
```

**Functions not working**
- Check environment variables: `firebase functions:config:get`
- View logs: Firebase Console → Functions → Logs

## Next Steps

1. **Add authentication** (optional but recommended)
   ```bash
   firebase console:open auth
   ```
   Enable Email/Password or Google sign-in

2. **Monitor your app**
   - Functions: Check logs in Firebase Console
   - Database: View Firestore data
   - Usage: Check free tier limits

3. **Update your app**
   ```bash
   # After changing code
   firebase deploy --only functions

   # After changing frontend
   firebase deploy --only hosting
   ```

## Cost Estimate

**Free tier limits:**
- 2M function calls/month
- 50K Firestore reads/day
- 10GB hosting storage

**Your app usage (estimated):**
- ~100 function calls/day
- ~500 Firestore reads/day
- ~1MB hosting

**Result: 100% FREE** ✨

## Need Help?

See the full [README.md](./README.md) for:
- Detailed configuration
- Security setup
- Advanced features
- Troubleshooting guide

---

**Ready? Run `./setup.sh` and you'll be live in 5 minutes!** 🚀
