// In-memory state store to persist data across navigation but reset on reload
const stateStore = {};

export const saveImageState = (id, state) => {
    stateStore[id] = state;
};

export const getImageState = (id) => {
    return stateStore[id];
};

export const clearImageState = (id) => {
    delete stateStore[id];
};
