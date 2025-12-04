import React, { useState } from 'react';
import Layout from './components/Layout';
import Library from './components/Library';
import AlbumView from './components/AlbumView';
import DetailView from './components/DetailView';
import { AnimatePresence } from 'framer-motion';

import SplashScreen from './components/SplashScreen';

const initialLocations = [
  {
    id: 1,
    title: 'Switzerland, Europe',
    date: 'November 16',
    photos: '05',
    folder: '/assets/card-images/switzerland',
    images: [
      '/assets/card-images/switzerland/1.png',
      '/assets/card-images/switzerland/2.png',
      '/assets/card-images/switzerland/3.png',
      '/assets/card-images/switzerland/4.png',
    ],
  },
  
  {
    id: 2,
    title: 'Germany, Europe',
    date: 'December 01',
    photos: '100',
    folder: '/assets/card-images/germany',
    images: [
      '/assets/card-images/germany/1.png',
      '/assets/card-images/germany/2.png',
      '/assets/card-images/germany/3.jpg',
      '/assets/card-images/germany/4.jpg',
    ],
  },
  {
    id: 3,
    title: 'Manali, India',
    date: 'August 05',
    photos: '478',
    folder: '/assets/card-images/manali',
    images: [
      '/assets/card-images/manali/1.png',
      '/assets/card-images/manali/2.png',
      '/assets/card-images/manali/3.png',
      '/assets/card-images/manali/4.png',
    ],
  },
  {
    id: 4,
    title: 'Prague, Europe',
    date: 'October 12',
    photos: '52',
    folder: '/assets/card-images/prague',
    images: [
      '/assets/card-images/prague/1.png',
      '/assets/card-images/prague/2.png',
      '/assets/card-images/prague/3.png',
      '/assets/card-images/prague/4.png',
    ],
  },
  {
    id: 5,
    title: 'Italy, Europe',
    date: 'September 20',
    photos: '100',
    folder: '/assets/card-images/Italy',
    images: [
      '/assets/card-images/Italy/1.png',
      '/assets/card-images/Italy/2.png',
      '/assets/card-images/Italy/3.png',
      '/assets/card-images/Italy/4.png',
    ],
  },
  {
    id: 6,
    title: 'Shimla, India',
    date: 'February 28',
    photos: '49',
    folder: '/assets/card-images/shimla',
    images: [
      '/assets/card-images/shimla/1.png',
      '/assets/card-images/shimla/2.png',
      '/assets/card-images/shimla/3.png',
      '/assets/card-images/shimla/4.png',
    ],
  },
  {
    id: 7,
    title: 'Paris, France',
    date: 'July 14',
    photos: '156',
    folder: '/assets/card-images/paris',
    images: [
      '/assets/card-images/paris/1.avif',
      '/assets/card-images/paris/2.avif',
      '/assets/card-images/paris/3.avif',
      '/assets/card-images/paris/4.avif',
    ],
  },
  {
    id: 8,
    title: 'Tokyo, Japan',
    date: 'March 22',
    photos: '234',
    folder: '/assets/card-images/tokyo',
    images: [
      '/assets/card-images/tokyo/4.avif',
      '/assets/card-images/tokyo/3.jpg',
      '/assets/card-images/tokyo/2.avif',
      '/assets/card-images/tokyo/1.avif',
    ],
  },
  {
    id: 9,
    title: 'Barcelona, Spain',
    date: 'June 10',
    photos: '89',
    folder: '/assets/card-images/barcelona',
    images: [
      '/assets/card-images/barcelona/1.avif',
      '/assets/card-images/barcelona/2.avif',
      '/assets/card-images/barcelona/3.avif',
      '/assets/card-images/barcelona/4.avif',
    ],
  },
  {
    id: 10,
    title: 'London, UK',
    date: 'May 05',
    photos: '312',
    folder: '/assets/card-images/london',
    images: [
      '/assets/card-images/london/1.avif',
      '/assets/card-images/london/2.avif',
      '/assets/card-images/london/3.avif',
      '/assets/card-images/london/4.avif',
    ],
  },
  {
    id: 11,
    title: 'Dubai, UAE',
    date: 'January 18',
    photos: '67',
    folder: '/assets/card-images/dubai',
    images: [
      '/assets/card-images/dubai/1.avif',
      '/assets/card-images/dubai/2.avif',
      '/assets/card-images/dubai/3.avif',
      '/assets/card-images/dubai/4.avif',
    ],
  },
  {
    id: 12,
    title: 'New York, USA',
    date: 'April 25',
    photos: '445',
    folder: '/assets/card-images/newyork',
    images: [
      '/assets/card-images/newyork/1.avif',
      '/assets/card-images/newyork/2.avif',
      '/assets/card-images/newyork/3.avif',
      '/assets/card-images/newyork/4.avif',
    ],
  },
];

function App() {
  const [loading, setLoading] = useState(true);
  const [currentScreen, setCurrentScreen] = useState('library');
  const [libraries, setLibraries] = useState(initialLocations);
  const [selectedLibraryId, setSelectedLibraryId] = useState(null);
  const [selectedPhoto, setSelectedPhoto] = useState(null);

  React.useEffect(() => {
    // Simulate initial loading time
    const timer = setTimeout(() => {
      setLoading(false);
    }, 2500);
    return () => clearTimeout(timer);
  }, []);

  const navigateToAlbum = (location) => {
    setSelectedLibraryId(location.id);
    setCurrentScreen('album');
  };

  const navigateToDetail = (photo) => {
    setSelectedPhoto(photo);
    setCurrentScreen('detail');
  };

  const navigateBackToLibrary = () => {
    setCurrentScreen('library');
    setTimeout(() => setSelectedLibraryId(null), 500);
  };

  const navigateBackToAlbum = () => {
    setCurrentScreen('album');
    setTimeout(() => setSelectedPhoto(null), 500);
  };

  const handleDeleteLibrary = (id) => {
    setLibraries(libraries.filter(lib => lib.id !== id));
  };

  const handleRenameLibrary = (id, newName) => {
    setLibraries(libraries.map(lib =>
      lib.id === id ? { ...lib, title: newName } : lib
    ));
  };

  const handleDeletePhotos = (libraryId, photoIds) => {
    setLibraries(libraries.map(lib => {
      if (lib.id === libraryId) {
        const newImages = lib.images.filter((_, index) => !photoIds.includes(index)); 
        const remainingImages = lib.images.filter((img, idx) => !photoIds.includes(idx));
        return {
          ...lib,
          images: remainingImages,
          photos: String(remainingImages.length)
        };
      }
      return lib;
    }));
  };

  const selectedLocation = libraries.find(lib => lib.id === selectedLibraryId);

  return (
    <>
      <AnimatePresence>
        {loading && <SplashScreen key="splash" />}
      </AnimatePresence>

      {!loading && (
        <Layout>
          <AnimatePresence mode="wait">
            {currentScreen === 'library' && (
              <Library
                key="library"
                onNavigate={navigateToAlbum}
                libraries={libraries}
                setLibraries={setLibraries}
                onDeleteLibrary={handleDeleteLibrary}
                onRenameLibrary={handleRenameLibrary}
              />
            )}
            {currentScreen === 'album' && (
              <AlbumView
                key="album"
                location={selectedLocation}
                onBack={navigateBackToLibrary}
                onSelectPhoto={navigateToDetail}
                onDeletePhotos={(photoIds) => handleDeletePhotos(selectedLocation.id, photoIds)}
              />
            )}
            {currentScreen === 'detail' && (
              <DetailView
                key="detail"
                location={selectedLocation} // Pass location for title
                photo={selectedPhoto}       // Pass specific photo
                onBack={navigateBackToAlbum}
              />
            )}
          </AnimatePresence>
        </Layout>
      )}
    </>
  );
}

export default App;
